"use strict";
const {chromium}=require("playwright");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const {pathToFileURL}=require("node:url");

(async()=>{
  const target=path.resolve(process.argv[2]);
  const folder=path.resolve("outputs/verificacao/filtros_cabecalho",path.basename(target,".html"));
  fs.mkdirSync(folder,{recursive:true});
  const browser=await chromium.launch({channel:"chrome",headless:true});
  try{
    const page=await browser.newPage({viewport:{width:1440,height:1050}});
    const errors=[],external=[];
    page.on("pageerror",e=>errors.push(String(e)));
    page.on("request",r=>{if(/^https?:/.test(r.url()))external.push(r.url());});
    await page.goto(pathToFileURL(target).href);
    const payload=await page.locator("#dados").textContent(),d=JSON.parse(payload);
    const names=d.rotulos_modelos||["Novo modelo","NEWAVE"];
    const months=["Janeiro","Fevereiro","Março","Abril","Maio","Junho","Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"];
    const statuses=["Dentro da tolerância","Fora da tolerância","sc"];
    const tabs={ordem:"Ordem PARP",mensais:"Coeficientes mensais",anual:"Coeficiente anual",medias_mensais:"Médias mensais",medias_anuais:"Médias anuais",desvio_mensal:"Desvio padrão mensal",desvio_anual:"Desvio padrão anual"};
    const camposEstatisticos={medias_mensais:"seasonal_mean_m3s",medias_anuais:"annual_mean_m3s",desvio_mensal:"seasonal_std_m3s",desvio_anual:"annual_std_m3s"};
    function rows(tab){
      const result=[];
      for(const p of d.linhas)for(let i=0;i<d.campos.length;i++){
        const field=d.campos[i],lag=field.startsWith("ar_coefficient_lag_");
        if(tab==="ordem"&&field!=="ar_order" || tab==="mensais"&&!lag || tab==="anual"&&field!=="annual_coefficient" || camposEstatisticos[tab]&&field!==camposEstatisticos[tab])continue;
        if(lag&&p[4][i]===null&&p[5][i]===null)continue;
        const r=[d.usinas[p[0]][0],d.meses[p[1]]];
        if(tab==="mensais")r.push(Number(field.split("_").at(-1)));
        r.push(p[4][i],p[5][i],p[6][i],p[8][i],p[7][i],field.endsWith("_m3s")?"m³/s":"Adimensional");
        if(tab==="mensais")r.push(p[7][i]!==2?"":p[4][i]===null?`Lag não ativo em ${names[0]} (p=${p[4][0]})`:`Lag não ativo em ${names[1]} (p=${p[5][0]})`,p[4][0],p[5][0]);
        result.push(r);
      }
      return result;
    }
    const table=()=>page.locator("[data-table]");
    async function count(){return Number((await table().locator(".contador").textContent()).match(/de (\d+) linhas/)[1]);}
    async function clear(){const bt=table().getByRole("button",{name:"Limpar filtros desta tabela",exact:true});if(await bt.isEnabled())await bt.click();}
    async function open(column){await table().getByRole("button",{name:"Filtrar coluna "+column,exact:true}).click();return page.getByRole("dialog");}
    function label(value,column){
      if(value==null)return "— (sem valor)";
      if(value==="")return "(Texto vazio)";
      if(column==="Mês do ano")return months[value-1];
      if(column==="Resultado")return statuses[value];
      return typeof value==="number" ? String(value).replace(".",",") : String(value);
    }
    async function selectValues(column,values){
      const menu=await open(column);
      await menu.getByRole("button",{name:"Desmarcar todos",exact:true}).click();
      for(const value of values){
        const text=label(value,column);
        await menu.getByRole("searchbox").fill(text);
        await menu.getByRole("checkbox",{name:text,exact:true}).check();
      }
      await menu.getByRole("button",{name:"Aplicar",exact:true}).click();
    }
    let columnsChecked=0;
    const baselineGeneral=await page.locator('[data-table="total"] tbody').textContent();
    // Exercitar todas as colunas, com dados que podem estar fora da primeira página.
    for(const [tab,title] of Object.entries(tabs)){
      await page.getByRole("tab",{name:title,exact:true}).click();
      const expected=rows(tab);
      const headers=await table().locator(".botao-filtro").evaluateAll(es=>es.map(e=>e.getAttribute("aria-label").replace("Filtrar coluna ","")));
      assert.equal(headers.length,expected[0].length);
      assert.equal(await count(),expected.length);
      for(let i=0;i<headers.length;i++){
        await clear();
        const value=expected.at(-1)[i];
        await selectValues(headers[i],[value]);
        assert.equal(await count(),expected.filter(r=>JSON.stringify(r[i]??null)===JSON.stringify(value??null)).length,tab+":"+headers[i]);
        assert.equal(await table().locator(".botao-filtro.ativo").count(),new Set(expected.map(r=>JSON.stringify(r[i]??null))).size>1?1:0,tab+":"+headers[i]);
        columnsChecked++;
      }
      await clear();
      await selectValues("Mês do ano",[1,3]);
      assert.equal(await count(),expected.filter(r=>[1,3].includes(r[1])).length);
      await selectValues("Usina",["CAMARGOS"]);
      const combined=expected.filter(r=>r[0]==="CAMARGOS"&&[1,3].includes(r[1]));
      assert.equal(await count(),combined.length);
      await page.getByRole("tab",{name:"Visão geral",exact:true}).click();
      assert.equal(await page.locator('[data-table="total"] tbody').textContent(),baselineGeneral);
      await page.getByRole("tab",{name:title,exact:true}).click();
      assert.equal(await count(),combined.length);
      const menu=await open("Usina");
      await menu.getByRole("button",{name:"Desmarcar todos",exact:true}).click();
      await menu.getByRole("button",{name:"Cancelar",exact:true}).click();
      assert.equal(await count(),combined.length);
      await open("Usina");await page.keyboard.press("Escape");
      assert.equal(await count(),combined.length);
      await clear();
    }
    await page.getByRole("tab",{name:tabs.mensais,exact:true}).click();
    const monthly=rows("mensais"),colA=3;
    // Condições numéricas usam valores reais completos, sem arredondar.
    for(const [operator,x,y,predicate] of [
      ["maior","-0,1",null,v=>v>-.1], ["menor","1e-3",null,v=>v<.001],
      ["maior_igual","0",null,v=>v>=0], ["menor_igual","0",null,v=>v<=0],
      ["igual","0",null,v=>v===0], ["diferente","0",null,v=>v!==0],
      ["entre","-0,1","0,5",v=>v>=-.1&&v<=.5]
    ]){
      await clear();const menu=await open(names[0]);
      await menu.getByRole("combobox").selectOption(operator);
      await menu.getByRole("textbox",{name:"Valor da condição",exact:true}).fill(x);
      if(y!==null)await menu.getByRole("textbox",{name:"Limite superior",exact:true}).fill(y);
      await menu.getByRole("button",{name:"Aplicar",exact:true}).click();
      assert.equal(await count(),monthly.filter(r=>typeof r[colA]==="number"&&predicate(r[colA])).length,operator);
    }
    await clear();
    let menu=await open(names[0]);
    await menu.getByRole("combobox").selectOption("entre");
    await menu.getByRole("textbox",{name:"Valor da condição",exact:true}).fill("abc");
    await menu.getByRole("button",{name:"Aplicar",exact:true}).click();
    assert(await menu.isVisible());
    assert.equal(await menu.getByRole("textbox",{name:"Valor da condição",exact:true}).evaluate(e=>e.validity.valid),false);
    await menu.getByRole("textbox",{name:"Valor da condição",exact:true}).fill("1");
    await menu.getByRole("textbox",{name:"Limite superior",exact:true}).fill("0");
    await menu.getByRole("button",{name:"Aplicar",exact:true}).click();
    assert(await menu.isVisible());await page.keyboard.press("Escape");
    assert.equal(await count(),monthly.length);
    for(const [operator,predicate] of [
      ["contem",v=>v.includes("cam")],["nao_contem",v=>!v.includes("cam")],
      ["igual",v=>v==="cam"],["diferente",v=>v!=="cam"],
      ["comeca",v=>v.startsWith("cam")],["termina",v=>v.endsWith("cam")]
    ]){
      await clear();menu=await open("Usina");
      await menu.getByRole("combobox").selectOption(operator);
      await menu.getByRole("textbox",{name:"Valor da condição",exact:true}).fill("CaM");
      await menu.getByRole("button",{name:"Aplicar",exact:true}).click();
      const normalized=v=>v.normalize("NFD").replace(/[\u0300-\u036f]/g,"").toLocaleLowerCase("pt-BR");
      assert.equal(await count(),monthly.filter(r=>predicate(normalized(r[0]))).length,operator);
    }
    await clear();
    const exact=monthly.find(r=>typeof r[colA]==="number")[colA];
    menu=await open(names[0]);await menu.getByRole("combobox").selectOption("igual");
    await menu.getByRole("textbox",{name:"Valor da condição",exact:true}).fill(String(exact).replace(".",","));
    await menu.getByRole("button",{name:"Aplicar",exact:true}).click();
    assert.equal(await count(),monthly.filter(r=>r[colA]===exact).length);
    await clear();
    if(monthly.some(r=>r[4]===null)){
      await selectValues(names[1],[null]);
      assert.equal(await count(),monthly.filter(r=>r[4]===null).length);
      await selectValues("Resultado",[2]);
      assert.equal(await count(),monthly.filter(r=>r[4]===null&&r[7]===2).length);
      await table().getByLabel("Resultado — Coeficientes mensais",{exact:true}).selectOption("0");
      assert.equal(await count(),0);
    }
    await clear();
    menu=await open("Usina");
    assert.equal(await menu.locator("input[data-valor]").count(),100);
    await menu.getByRole("button",{name:/Mostrar mais/}).click();
    assert.equal(await menu.locator("input[data-valor]").count(),new Set(monthly.map(r=>r[0])).size);
    await page.keyboard.press("Escape");
    await table().getByLabel("Linhas por página — Coeficientes mensais",{exact:true}).selectOption("25");
    await table().getByRole("button",{name:"Próxima",exact:true}).click();
    await selectValues("Mês do ano",[1]);
    assert((await table().locator(".paginacao").textContent()).includes("Página 1 de"));
    await clear();
    // Lista vazia deve filtrar tudo; limpar somente a coluna restaura os dados.
    menu=await open("Lag");await menu.getByRole("button",{name:"Desmarcar todos",exact:true}).click();
    await menu.getByRole("button",{name:"Aplicar",exact:true}).click();assert.equal(await count(),0);
    menu=await open("Lag");await menu.getByRole("button",{name:"Limpar coluna",exact:true}).click();assert.equal(await count(),monthly.length);
    // Buscar opções e aplicar somente os resultados, incluindo páginas não visíveis.
    menu=await open("Usina");await menu.getByRole("searchbox").fill("camargos");
    await menu.getByRole("button",{name:"Somente resultados da busca",exact:true}).click();
    await menu.getByRole("button",{name:"Aplicar",exact:true}).click();
    assert.equal(await count(),monthly.filter(r=>r[0]==="CAMARGOS").length);
    await selectValues("Mês do ano",[1,3]);
    menu=await open("Diferença absoluta");
    await menu.getByRole("combobox").selectOption("maior");
    await menu.getByRole("textbox",{name:"Valor da condição",exact:true}).fill("0");
    await page.screenshot({path:path.join(folder,"menu_filtro_numerico.png")});
    await menu.getByRole("button",{name:"Aplicar",exact:true}).click();
    const filtered=monthly.filter(r=>r[0]==="CAMARGOS"&&[1,3].includes(r[1])&&typeof r[5]==="number"&&r[5]>0);
    assert.equal(await count(),filtered.length);
    await page.screenshot({path:path.join(folder,"filtros_combinados.png")});
    // Os filtros locais devem sobreviver ao recorte geral e continuar na aba.
    await page.locator("#fim").selectOption("12");await page.locator("#inicio").selectOption("12");
    assert.equal(await count(),filtered.filter(r=>r[1]===1).length);
    await page.locator("#limpar").click();assert.equal(await count(),monthly.length);
    assert.equal(await table().locator(".botao-filtro.ativo").count(),0);
    for(const title of Object.values(tabs)){
      await page.getByRole("tab",{name:title,exact:true}).click();
      assert.equal(await table().locator(".botao-filtro.ativo").count(),0);
    }
    assert.equal(await page.locator("#dados").textContent(),payload);
    assert.deepEqual(errors,[]);assert.deepEqual(external,[]);
    const result={html:target,colunas_conferidas:columnsChecked,multisselecao:true,filtros_combinados:true,
      condicoes_numericas:8,condicoes_texto:6,invalidos_rejeitados:true,entre_inclusivo:true,estado_por_aba:true,
      nulos_e_sc:monthly.some(r=>r[4]===null)?"conferidos":"sem casos nesta fonte",listas_com_mais_de_100_valores:true,paginacao_reiniciada:true,
      cancelar_e_escape:true,limpar_coluna_tabela_e_global:true,recorte_geral:true,
      valores_incorporados_preservados:true,erros:errors,requisicoes_externas:external};
    fs.writeFileSync(path.join(folder,"resultado.json"),JSON.stringify(result,null,2));console.log(JSON.stringify(result,null,2));
  }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
