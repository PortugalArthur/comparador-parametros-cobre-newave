"use strict";
// Exercita a preparação das tabelas do JavaScript real. A construção visual
// do DOM é substituída pela captura das linhas antes da paginação.
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const assert = require("node:assert/strict");
const root = path.resolve(__dirname, "..");
const files = fs.readdirSync(path.join(root, "relatorios"))
  .filter(f => f.endsWith(".html"))
  .map(f => path.join(root, "relatorios", f))
  .sort((a,b) => fs.statSync(b).mtimeMs - fs.statSync(a).mtimeMs);
const html = fs.readFileSync(files[0], "utf8");
const jsonText = html.match(/<script id="dados" type="application\/json">([\s\S]*?)<\/script>/)[1];
const data = JSON.parse(jsonText);
let code = fs.readFileSync(path.join(root, "recursos/interacao.js"), "utf8");
assert(html.includes(code));
const begin = code.indexOf("  function tabela(");
const end = code.indexOf("  function mostrarGeral()");
assert(begin >= 0 && end > begin);
code = code.slice(0, begin) + `
  function tabela(id,titulo,descricao,colunas,linhas,ordem=0,direcao=1,filtrarStatus=false){
    globalThis.captures.push({id,titulo,colunas,linhas,ordem,direcao,filtrarStatus});
  }
` + code.slice(end);
const setup = code.indexOf('\n  document.querySelectorAll("[data-tab]").forEach(bt=>{');
assert(setup > 0);
code = code.slice(0, setup) + `
  globalThis.auditApi={setTab:t=>{aba=t;},filtrar,comparar};
})();`;
const nodes = {};
function node(id) {
  if(!nodes[id]) nodes[id]={value:"",textContent:"",replaceChildren(){},setAttribute(){}};
  return nodes[id];
}
node("dados").textContent=jsonText;
const sandbox={captures:[],document:{getElementById:node},Intl,Map,Set,console};
vm.createContext(sandbox);
vm.runInContext(code,sandbox);
const api=sandbox.auditApi;
const plain=x=>JSON.parse(JSON.stringify(x));
const normal=s=>String(s).normalize("NFD").replace(/[\u0300-\u036f]/g,"").toUpperCase().replace(/[^A-Z0-9]/g,"");
function selected(search,start,finish){
  const isId=/^\d+$/.test(search.trim());
  return data.linhas.filter(p=>{
    const u=data.usinas[p[0]];
    const plant=!normal(search)||(isId?u[1]===Number(search)||u[2]===Number(search):normal(u[0]).includes(normal(search)));
    return plant&&p[1]>=start&&p[1]<=finish;
  });
}
function tally(rows){
  let inside=0,outside=0,sc=0;
  for(const p of rows)for(let i=0;i<data.campos.length;i++){
    if(data.campos[i].startsWith("ar_coefficient_lag_")&&p[4][i]===null&&p[5][i]===null)continue;
    if(p[7][i]===0)inside++;else if(p[7][i]===1)outside++;else sc++;
  }
  const n=inside+outside;
  return [n,inside,outside,n?100*inside/n:null,sc];
}
let checkedDetails=0,checkedSummaries=0;
const selections=[
  ["",0,data.datas.length-1],
  ["PIMENTAL",0,data.datas.length-1],
  ["",6,11],
  ["145",0,0],
  ["USINA_INEXISTENTE_1234567",0,data.datas.length-1]
];
for(const [search,start,finish] of selections){
  node("busca").value=search;node("inicio").value=String(start);node("fim").value=String(finish);
  const rows=selected(search,start,finish);
  api.setTab("geral");sandbox.captures=[];api.filtrar();
  const summaries=plain(sandbox.captures);
  const total=summaries.find(t=>t.id==="total").linhas[0];
  assert.deepEqual(total,[new Set(rows.map(p=>p[0])).size,new Set(rows.map(p=>p[1])).size,rows.length,...tally(rows)]);
  const byPlant=summaries.find(t=>t.id==="usinas");
  assert.equal(byPlant.ordem,4);assert.equal(byPlant.direcao,-1);
  for(const r of byPlant.linhas){
    const subset=rows.filter(p=>data.usinas[p[0]][0]===r[0]);
    assert.deepEqual(r,[r[0],subset.length,...tally(subset)]);checkedSummaries++;
  }
  for(const r of summaries.find(t=>t.id==="meses").linhas){
    const subset=rows.filter(p=>data.datas[p[1]]===r[0]);
    assert.deepEqual(r,[r[0],subset.length,...tally(subset)]);checkedSummaries++;
  }
  for(const tab of ["ordem","mensais","anual","estatisticas"]){
    api.setTab(tab);sandbox.captures=[];api.filtrar();
    assert.equal(sandbox.captures.length,1);
    const table=plain(sandbox.captures[0]);
    const headers=table.colunas.map(c=>c.nome);
    assert.equal(headers[headers.indexOf("Resultado")+1],"Unidade");
    if(tab==="mensais") assert.deepEqual(headers.slice(-2),["Ordem novo modelo","Ordem NEWAVE"]);
    assert(!headers.some(h=>/^(Id|Estágio) /i.test(h)));
    const expected=[];
    for(const p of rows)for(let i=0;i<data.campos.length;i++){
      const field=data.campos[i],lag=field.startsWith("ar_coefficient_lag_");
      if(tab==="ordem"&&field!=="ar_order")continue;
      if(tab==="mensais"&&!lag)continue;
      if(tab==="anual"&&field!=="annual_coefficient")continue;
      if(tab==="estatisticas"&&!field.endsWith("_m3s"))continue;
      if(lag&&p[4][i]===null&&p[5][i]===null)continue;
      const r=[data.usinas[p[0]][0],data.datas[p[1]]];
      if(tab==="mensais")r.push(Number(field.split("_").at(-1)));
      if(tab==="estatisticas")r.push(data.nomes_campos[i]);
      r.push(p[4][i],p[5][i],p[6][i],p[8][i],p[7][i],field.endsWith("_m3s")?"m³/s":"Adimensional");
      if(tab==="mensais")r.push(p[7][i]!==2?"":p[4][i]===null?`Lag não ativo no novo modelo (p=${p[4][0]})`:`Lag não ativo no NEWAVE (p=${p[5][0]})`,p[4][0],p[5][0]);
      expected.push(r);
    }
    assert.deepEqual(table.linhas,expected);checkedDetails+=expected.length;
  }
}
assert.equal(api.comparar(2,10,"numero",1),-8);
assert.equal(api.comparar(2,10,"numero",-1),8);
assert.equal(api.comparar(null,10,"numero",1),1);
assert.equal(api.comparar(null,10,"numero",-1),1);
const result={html:files[0],selecoes:selections.length,linhas_detalhe_conferidas:checkedDetails,
  resumos_usina_mes_conferidos:checkedSummaries,ordenacao_numerica:true,unidade_a_direita:true,
  ordens_ao_final_da_tabela_mensal:true,divergencias:0,
  escopo:"Preparação das tabelas, resumos, filtros e comparador de ordenação; sem inspeção visual do navegador."};
const folder=path.join(root,"outputs/verificacao/auditoria_html_2026_11_01");
fs.mkdirSync(folder,{recursive:true});
fs.writeFileSync(path.join(folder,"tabelas.json"),JSON.stringify(result,null,2));
console.log(JSON.stringify(result,null,2));
