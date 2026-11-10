"use strict";
// NODE_PATH deve apontar para as bibliotecas locais que contêm playwright.
const {chromium} = require("playwright");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const {pathToFileURL} = require("node:url");

(async()=>{
  const target=path.resolve(process.argv[2]);
  const folder=path.resolve("outputs/verificacao/consolidacao_mensal",path.basename(target,".html"));
  fs.mkdirSync(folder,{recursive:true});
  const browser=await chromium.launch({channel:"chrome",headless:true});
  try{
    const page=await browser.newPage({viewport:{width:1440,height:1000}});
    const errors=[],external=[];
    page.on("pageerror",e=>errors.push(String(e)));
    page.on("request",r=>{if(/^https?:/.test(r.url()))external.push(r.url());});
    await page.goto(pathToFileURL(target).href);
    await page.locator('[data-table="total"] tbody tr').waitFor();
    const d=await page.locator("#dados").evaluate(e=>JSON.parse(e.textContent));
    assert.equal(d.versao,6);
    assert.equal(await page.getByRole("tab").count(),8);
    assert((await page.locator("#identificacao").textContent()).includes("12 meses do ano"));
    const total=await page.locator('[data-table="total"] tbody tr').innerText();
    assert(total.includes(String(d.linhas.length)));
    await page.screenshot({path:path.join(folder,"visao_geral.png")});
    await page.locator("#busca").fill("CAMARGOS");
    await page.waitForFunction(()=>document.getElementById("escopo").textContent.startsWith("1 usina(s)"));
    await page.getByRole("tab",{name:"Ordem PARP",exact:true}).click();
    const order=page.locator('[data-table="ordem"]');
    assert.equal(await order.locator("tbody tr").count(),12);
    const months=await order.locator("tbody tr td:nth-child(2)").allTextContents();
    assert.deepEqual(months,["Janeiro","Fevereiro","Março","Abril","Maio","Junho","Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"]);
    await order.getByRole("button",{name:"Ordenar por Mês do ano",exact:true}).click();
    await order.getByRole("button",{name:"Ordenar por Mês do ano",exact:true}).click();
    assert.deepEqual(await order.locator("tbody tr td:nth-child(2)").allTextContents(),months.slice().reverse());
    // O segundo ano completo não pode apagar nem duplicar os conjuntos mensais.
    await page.locator("#fim").selectOption("23");
    await page.locator("#inicio").selectOption("12");
    assert.equal(await order.locator("tbody tr").count(),12);
    await page.locator("#fim").selectOption("12");
    assert.equal(await order.locator("tbody tr").count(),1);
    assert.equal(await order.locator("tbody tr td:nth-child(2)").textContent(),"Janeiro");
    await page.locator("#inicio").selectOption("11");
    await page.locator("#fim").selectOption("13");
    assert.equal(await order.locator("tbody tr").count(),3);
    await page.locator("#limpar").click();
    assert.equal(await order.locator("tbody tr").count(),100);
    const first=await order.locator("tbody tr").first().innerText();
    await order.getByRole("button",{name:"Próxima",exact:true}).click();
    assert.notEqual(await order.locator("tbody tr").first().innerText(),first);
    await page.locator("#busca").fill("CAMARGOS");
    await page.waitForFunction(()=>document.getElementById("escopo").textContent.startsWith("1 usina(s)"));
    for(const tab of ["Coeficientes mensais","Coeficiente anual","Médias mensais","Médias anuais","Desvio padrão mensal","Desvio padrão anual"]){
      await page.getByRole("tab",{name:tab,exact:true}).click();
      const table=page.locator("[data-table]");
      const headers=await table.locator("th").allTextContents();
      assert(headers[1].includes("Mês do ano"));
      const status=headers.findIndex(t=>t.includes("Resultado"));
      assert(headers[status+1].includes("Unidade"));
      if(["Médias mensais","Médias anuais","Desvio padrão mensal","Desvio padrão anual"].includes(tab))assert.equal(await table.locator("tbody tr").count(),12);
      if(tab==="Coeficiente anual")assert.equal(await table.locator("tbody tr").count(),12);
      await table.getByLabel("Resultado — "+tab,{exact:true}).selectOption("1");
      const badges=await table.locator("tbody .selo").allTextContents();
      assert(badges.every(t=>t==="Fora da tolerância"));
      await table.getByLabel("Resultado — "+tab,{exact:true}).selectOption("todos");
    }
    // Cada nova aba deve manter seu próprio filtro de cabeçalho.
    const separadas=["Médias mensais","Médias anuais","Desvio padrão mensal","Desvio padrão anual"];
    for(let i=0;i<separadas.length;i++){
      await page.getByRole("tab",{name:separadas[i],exact:true}).click();
      assert.equal(await page.locator("[data-table] tbody tr").count(),12);
      await page.getByRole("button",{name:"Filtrar coluna Mês do ano",exact:true}).click();
      const menu=page.getByRole("dialog");
      await menu.getByRole("button",{name:"Desmarcar todos",exact:true}).click();
      const month=["Janeiro","Fevereiro","Março","Abril"][i];
      await menu.getByRole("checkbox",{name:month,exact:true}).check();
      await menu.getByRole("button",{name:"Aplicar",exact:true}).click();
      assert.equal(await page.locator("[data-table] tbody tr").count(),1);
    }
    for(let i=0;i<separadas.length;i++){
      await page.getByRole("tab",{name:separadas[i],exact:true}).click();
      assert.equal(await page.locator("[data-table] tbody tr td:nth-child(2)").textContent(),["Janeiro","Fevereiro","Março","Abril"][i]);
    }
    await page.locator("#limpar").click();
    await page.locator("#busca").fill("CAMARGOS");
    await page.waitForFunction(()=>document.getElementById("escopo").textContent.startsWith("1 usina(s)"));
    await page.getByRole("tab",{name:"Médias anuais",exact:true}).click();
    assert((await page.locator(".descricao").textContent()).includes("Média da componente anual"));
    await page.screenshot({path:path.join(folder,"medias_anuais.png")});
    await page.getByRole("tab",{name:"Médias anuais",exact:true}).press("End");
    assert.equal(await page.getByRole("tab",{selected:true}).textContent(),"Desvio padrão anual");
    await page.getByRole("tab",{name:"Desvio padrão anual",exact:true}).press("Home");
    assert.equal(await page.getByRole("tab",{selected:true}).textContent(),"Visão geral");
    await page.getByRole("tab",{name:"Coeficientes mensais",exact:true}).click();
    await page.setViewportSize({width:1100,height:900});
    await page.waitForTimeout(100);
    const scroll=page.locator('[data-table="mensais"] .tabela-scroll');
    await scroll.evaluate(e=>{e.scrollLeft=250;});
    await page.waitForTimeout(100);
    const positions=await page.locator('[data-table="mensais"]').evaluate(e=>({
      top:e.querySelector(".tabela-scroll-topo").scrollLeft,
      bottom:e.querySelector(".tabela-scroll").scrollLeft,
      hidden:e.querySelector(".tabela-scroll-topo").hidden
    }));
    assert.equal(positions.hidden,false);
    assert(positions.bottom>0);
    assert.equal(positions.top,positions.bottom);
    await scroll.evaluate(e=>{e.scrollLeft=0;});
    await page.setViewportSize({width:1440,height:1000});
    await page.screenshot({path:path.join(folder,"coeficientes_camargos.png")});
    assert.deepEqual(errors,[]);
    assert.deepEqual(external,[]);
    const result={html:target,abas:8,meses_em_ordem:true,filtro_segundo_ano:true,
      intervalo_com_virada_de_ano:true,paginacao:true,filtro_resultado:true,
      unidade_a_direita:true,rolagem_sincronizada:true,erros:errors,requisicoes_externas:external};
    fs.writeFileSync(path.join(folder,"navegador.json"),JSON.stringify(result,null,2));
    console.log(JSON.stringify(result,null,2));
  }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
