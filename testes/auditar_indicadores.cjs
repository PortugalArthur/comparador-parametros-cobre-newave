"use strict";
const {chromium}=require("playwright");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const {pathToFileURL}=require("node:url");

(async()=>{
  const file=path.resolve(process.argv[2]);
  const folder=path.resolve("outputs/verificacao/indicadores",path.basename(file,".html"));
  fs.mkdirSync(folder,{recursive:true});
  const browser=await chromium.launch({channel:"chrome",headless:true});
  try{
    const page=await browser.newPage({viewport:{width:1440,height:1250}}),errors=[],external=[];
    page.on("pageerror",e=>errors.push(String(e)));
    page.on("request",r=>{if(/^https?:/.test(r.url()))external.push(r.url());});
    await page.goto(pathToFileURL(file).href);
    const payload=await page.locator("#dados").textContent(),d=JSON.parse(payload);
    const names=d.rotulos_modelos||["Novo modelo","NEWAVE"];
    const titles={geral:"Visão geral",ordem:"Ordem PARP",mensais:"Coeficientes mensais",anual:"Coeficiente anual",medias_mensais:"Médias mensais",medias_anuais:"Médias anuais",desvio_mensal:"Desvio padrão mensal",desvio_anual:"Desvio padrão anual"};
    const months=["Janeiro","Fevereiro","Março","Abril","Maio","Junho","Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"];
    const fmt=new Intl.NumberFormat("pt-BR",{useGrouping:false,maximumSignificantDigits:15});
    const pct=new Intl.NumberFormat("pt-BR",{useGrouping:false,minimumFractionDigits:2,maximumFractionDigits:2});
    const camposEstatisticos={medias_mensais:"seasonal_mean_m3s",medias_anuais:"annual_mean_m3s",desvio_mensal:"seasonal_std_m3s",desvio_anual:"annual_std_m3s"};
    function records(tab){
      const result=[];
      for(const p of d.linhas)for(let i=0;i<d.campos.length;i++){
        const field=d.campos[i],lag=field.startsWith("ar_coefficient_lag_");
        if(tab==="ordem"&&field!=="ar_order" || tab==="mensais"&&!lag || tab==="anual"&&field!=="annual_coefficient" || camposEstatisticos[tab]&&field!==camposEstatisticos[tab])continue;
        if(lag&&p[4][i]===null&&p[5][i]===null)continue;
        result.push({plant:d.usinas[p[0]][0],month:d.meses[p[1]],status:p[7][i],field,a:p[4][i],diff:p[6][i]});
      }
      return result;
    }
    function expected(rows){
      const all=rows,failed=rows.filter(r=>r.status!==0),approved=rows.filter(r=>r.status===0);
      const pairCount=rs=>new Set(rs.map(r=>JSON.stringify([r.plant,r.month]))).size;
      const aprovadosPorGrupo=key=>{
        const groups=new Map();
        for(const r of all){const k=key(r);if(!groups.has(k))groups.set(k,[]);groups.get(k).push(r);}
        return Array.from(groups.values()).filter(rs=>rs.every(r=>r.status===0)).length;
      };
      return {combinacoes:pairCount(all),combinacoes_reprovadas:pairCount(failed),
        combinacoes_aprovadas:aprovadosPorGrupo(r=>JSON.stringify([r.plant,r.month])),
        usinas_aprovadas:aprovadosPorGrupo(r=>r.plant),aprovados:approved.length,
        taxa_aprovacao:all.length?100*approved.length/all.length:null,
        usinas_reprovadas:new Set(failed.map(r=>r.plant)).size,
        taxa_reprovacao:all.length?100*failed.length/all.length:null,
        usinas:new Set(all.map(r=>r.plant)).size,avaliados:all.length,
        reprovados:failed.length,sc:all.filter(r=>r.status===2).length};
    }
    let checks=0;
    async function verify(rows,reason){
      const exp=expected(rows);
      assert.equal(exp.aprovados+exp.reprovados,exp.avaliados);
      assert.equal(exp.combinacoes_aprovadas+exp.combinacoes_reprovadas,exp.combinacoes);
      assert.equal(exp.usinas_aprovadas+exp.usinas_reprovadas,exp.usinas);
      if(rows.length && rows.every(r=>r.status===2)){
        assert.equal(exp.aprovados,0);assert.equal(exp.taxa_reprovacao,100);
      }
      const tab=await page.getByRole("tab",{selected:true}).getAttribute("data-tab");
      if(tab==="geral"){
        assert.equal(await page.locator("[data-indicador], [data-table=total]").count(),0);
        checks++;return exp;
      }
      const temCombinacoes=tab==="mensais";
      assert.equal(await page.locator("[data-indicador]").count(),tab==="mensais"?12:8);
      for(const [key,value] of Object.entries(exp)){
        if(key.startsWith("combinacoes") && !temCombinacoes){
          assert.equal(await page.locator(`[data-indicador="${key}"]`).count(),0);continue;
        }
        if(key==="sc" && tab!=="mensais"){
          assert.equal(await page.locator('[data-indicador="sc"]').count(),0);continue;
        }
        const actual=await page.locator(`[data-indicador="${key}"] .indicador-valor`).textContent();
        assert.equal(actual,value===null?"—":key.startsWith("taxa_")?pct.format(value)+"%":fmt.format(value),reason+":"+key);
      }
      checks++;
      return exp;
    }
    async function selectMonths(values){
      await page.getByRole("button",{name:"Filtrar coluna Mês do ano",exact:true}).click();
      const menu=page.getByRole("dialog");
      await menu.getByRole("button",{name:"Desmarcar todos",exact:true}).click();
      for(const n of values)await menu.getByRole("checkbox",{name:months[n-1],exact:true}).check();
      await menu.getByRole("button",{name:"Aplicar",exact:true}).click();
    }
    const baselines={};
    for(const [tab,title] of Object.entries(titles)){
      await page.getByRole("tab",{name:title,exact:true}).click();
      const all=records(tab);
      baselines[tab]=await verify(all,tab+":sem filtros");
      if(tab==="geral")continue;
      const table=page.locator(`[data-table="${tab}"]`);
      if(tab==="ordem")await page.screenshot({path:path.join(folder,"ordem.png")});
      if(tab==="mensais")await page.screenshot({path:path.join(folder,"coeficientes_mensais.png")});
      const result=table.getByLabel("Resultado — "+title,{exact:true});
      for(const status of [1,0,2,"reprovados"]){
        await result.selectOption(String(status));
        await verify(all.filter(r=>status==="reprovados" ? r.status!==0 : r.status===status),tab+":resultado "+status);
      }
      await result.selectOption("todos");
      await selectMonths([1,3]);
      let subset=all.filter(r=>[1,3].includes(r.month));
      await verify(subset,tab+":meses");
      await result.selectOption("1");
      await verify(subset.filter(r=>r.status===1),tab+":meses e reprovados");
      await result.selectOption("todos");
      await page.getByRole("button",{name:"Filtrar coluna "+names[0],exact:true}).click();
      const menu=page.getByRole("dialog");
      await menu.getByRole("combobox").selectOption("maior");
      await menu.getByRole("textbox",{name:"Valor da condição",exact:true}).fill("0,1");
      await menu.getByRole("button",{name:"Aplicar",exact:true}).click();
      subset=subset.filter(r=>typeof r.a==="number"&&r.a>.1);
      await verify(subset,tab+":meses e número");
      // Ordenação, tamanho da página e mudança de página não alteram os cartões.
      await table.getByLabel("Linhas por página — "+title,{exact:true}).selectOption("25");
      await table.getByRole("button",{name:"Ordenar por Usina",exact:true}).click();
      await verify(subset,tab+":ordenação e tamanho de página");
      const next=table.getByRole("button",{name:"Próxima",exact:true});
      if(await next.isEnabled()){await next.click();await verify(subset,tab+":segunda página");}
      await page.getByRole("tab",{name:titles.geral,exact:true}).click();
      await verify(records("geral"),tab+":filtro local não altera visão geral");
      await page.getByRole("tab",{name:title,exact:true}).click();
      await verify(subset,tab+":retorno à aba");
      await page.locator("#busca").fill("CAMARGOS");
      await page.waitForFunction(()=>document.getElementById("escopo").textContent.startsWith("1 usina(s)"));
      await verify(subset.filter(r=>r.plant==="CAMARGOS"),tab+":usina geral e filtros locais");
      await page.locator("#fim").selectOption("12");await page.locator("#inicio").selectOption("12");
      await verify(subset.filter(r=>r.plant==="CAMARGOS"&&r.month===1),tab+":intervalo e filtros locais");
      await selectMonths([]);await verify([],tab+":nenhuma seleção");
      await page.locator("#limpar").click();await verify(all,tab+":limpeza global");
    }
    assert.equal(await page.getByRole("tab").count(),8);
    assert.equal(Object.keys(camposEstatisticos).reduce((n,k)=>n+baselines[k].avaliados,0),d.linhas.length*4);
    await page.getByRole("tab",{name:titles.geral,exact:true}).click();
    await page.locator("#busca").fill("CAMARGOS");
    await page.waitForFunction(()=>document.getElementById("escopo").textContent.startsWith("1 usina(s)"));
    await verify(records("geral").filter(r=>r.plant==="CAMARGOS"),"visão geral por usina");
    await page.locator("#busca").fill("USINA_INEXISTENTE_12345");
    await page.waitForFunction(()=>document.getElementById("escopo").textContent.startsWith("0 usina(s)"));
    await verify([],"visão geral vazia");
    await page.locator("#limpar").click();await verify(records("geral"),"visão geral restaurada");
    await page.screenshot({path:path.join(folder,"visao_geral.png")});
    await page.getByRole("tab",{name:titles.ordem,exact:true}).click();
    await page.setViewportSize({width:390,height:900});
    assert(await page.locator(".indicadores-grade").evaluate(e=>e.getBoundingClientRect().right<=window.innerWidth));
    assert(await page.locator(".indicadores-grade").evaluate(e=>getComputedStyle(e).gridTemplateColumns.split(" ").length===1));
    assert.equal(await page.locator("#dados").textContent(),payload);
    assert.deepEqual(errors,[]);assert.deepEqual(external,[]);
    const result={html:file,conferencias:checks,cartoes_por_aba:{mensais:12,geral:0,demais:8},combinacoes_apenas_mensais:true,sc_no_cartao_reprovados:true,contador_sc_amarelo_apenas_mensais:true,abas:8,sem_duplicar_usinas_e_combinacoes:true,
      aprovacao_exige_ausencia_de_reprovacao_ou_sc:true,
      sc_conta_como_reprovado:true,taxas_incluem_sc:true,taxa_sem_linhas:"—",filtros_gerais_resultado_e_cabecalho:true,
      independente_da_paginacao:true,responsivo:true,dados_preservados:true,baselines,erros:errors,requisicoes_externas:external};
    fs.writeFileSync(path.join(folder,"resultado.json"),JSON.stringify(result,null,2));console.log(JSON.stringify(result,null,2));
  }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
