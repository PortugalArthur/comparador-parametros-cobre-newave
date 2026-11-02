"use strict";
(() => {
  const D = JSON.parse(document.getElementById("dados").textContent);
  const $ = id => document.getElementById(id);
  const numero = new Intl.NumberFormat("pt-BR", {useGrouping:false, maximumSignificantDigits:15});
  const percentual = new Intl.NumberFormat("pt-BR", {useGrouping:false, minimumFractionDigits:2, maximumFractionDigits:2});
  const mes = d => d.slice(5,7) + "/" + d.slice(0,4);
  const normalizar = s => String(s).normalize("NFD").replace(/[\u0300-\u036f]/g, "").toUpperCase().replace(/[^A-Z0-9]/g, "");
  const nomesStatus = ["Dentro da tolerância", "Fora da tolerância", "sc"];
  const classesStatus = ["dentro", "fora", "sc"];
  const tabNames = {geral:"Visão geral", ordem:"Ordem PARP", mensais:"Coeficientes mensais", anual:"Coeficiente anual", estatisticas:"Médias e desvios padrão"};
  const indices = D.campos.map((campo, i) => ({campo,i, lag:campo.startsWith("ar_coefficient_lag_")}));
  const estados = new Map();
  const observadoresRolagem = new Set();
  let aba = "geral", pares = D.linhas, atrasoBusca;

  function el(tag, texto, classe) {
    const e = document.createElement(tag);
    if (texto !== undefined && texto !== null) e.textContent = texto;
    if (classe) e.className = classe;
    return e;
  }
  function opcoes(select, valores) {
    for (const [valor, texto] of valores) {
      const o = el("option", texto); o.value = valor; select.append(o);
    }
  }
  function camposAtivos(p, cb) {
    for (const {i,lag} of indices) {
      if (lag && p[4][i] === null && p[5][i] === null) continue;
      cb(i, p[7][i]);
    }
  }
  function resumo() { return {pares:0, dentro:0, fora:0, sc:0}; }
  function somar(r, s) { r[s === 0 ? "dentro" : s === 1 ? "fora" : "sc"]++; }
  function valoresResumo(r) {
    const n = r.dentro + r.fora;
    return [n, r.dentro, r.fora, n ? 100*r.dentro/n : null, r.sc];
  }
  const col = (nome,tipo="texto") => ({nome,tipo});
  const colsResumo = [col("Comparáveis","numero"),col("Dentro da tolerância","numero"),col("Fora da tolerância","numero"),col("Dentro (%)","percentual"),col("sc","numero")];

  function comparar(a,b,tipo,direcao) {
    if (a === null || a === undefined) return b === null || b === undefined ? 0 : 1;
    if (b === null || b === undefined) return -1;
    let v;
    if (["numero","percentual","status"].includes(tipo) && typeof a==="number" && typeof b==="number") v = a-b;
    else v = String(a).localeCompare(String(b),"pt-BR",{numeric:true,sensitivity:"base"});
    return v*direcao;
  }
  function tabela(id, titulo, descricao, colunas, linhas, ordem=0, direcao=1, filtrarStatus=false) {
    let estado = estados.get(id);
    if (!estado) { estado={ordem,direcao,pagina:0,tamanho:100,status:"todos"}; estados.set(id,estado); }
    const painel = el("section", null, "painel"); painel.dataset.table = id;
    painel.append(el("h2",titulo),el("p",descricao,"descricao"));
    const conteudo = el("div"); painel.append(conteudo);
    let observadorRolagem = null;
    function desenhar() {
      if (observadorRolagem) {
        observadorRolagem.disconnect();
        observadoresRolagem.delete(observadorRolagem);
      }
      conteudo.replaceChildren();
      const toolbar = el("div",null,"toolbar");
      const tamanhoLabel = el("label","Linhas por página");
      const tamanho = el("select"); tamanho.setAttribute("aria-label","Linhas por página — "+titulo);
      opcoes(tamanho, [25,50,100,250].map(n=>[n,n])); tamanho.value=estado.tamanho;
      tamanho.addEventListener("change",()=>{estado.tamanho=Number(tamanho.value);estado.pagina=0;desenhar();});
      tamanhoLabel.append(tamanho); toolbar.append(tamanhoLabel);
      if (filtrarStatus) {
        const label=el("label","Resultado"); const filtro=el("select");
        filtro.setAttribute("aria-label","Resultado — "+titulo);
        opcoes(filtro,[["todos","Todos"],["0",nomesStatus[0]],["1",nomesStatus[1]],["2","sc — sem comparação"]]);
        filtro.value=estado.status;
        filtro.addEventListener("change",()=>{estado.status=filtro.value;estado.pagina=0;desenhar();});
        label.append(filtro);toolbar.append(label);
      }
      const statusCol = colunas.findIndex(c=>c.tipo==="status");
      const visiveis = estado.status === "todos" || statusCol < 0 ? linhas.slice() : linhas.filter(r=>r[statusCol]===Number(estado.status));
      visiveis.sort((a,b)=>comparar(a[estado.ordem],b[estado.ordem],colunas[estado.ordem].tipo,estado.direcao));
      const paginas=Math.max(1,Math.ceil(visiveis.length/estado.tamanho));
      estado.pagina=Math.min(estado.pagina,paginas-1);
      const inicio=estado.pagina*estado.tamanho, fim=Math.min(inicio+estado.tamanho,visiveis.length);
      const contagem=el("span",`${visiveis.length ? inicio+1 : 0}–${fim} de ${visiveis.length} linhas`,"contador");
      toolbar.append(contagem);conteudo.append(toolbar);
      const scroll=el("div",null,"tabela-scroll"); scroll.tabIndex=0;scroll.setAttribute("aria-label",titulo);
      const table=el("table"); const head=el("thead"), tr=el("tr");
      colunas.forEach((c,i)=>{
        const th=el("th");th.scope="col";
        if(i===estado.ordem) th.setAttribute("aria-sort",estado.direcao===1?"ascending":"descending");
        const bt=el("button");bt.type="button";bt.append(el("span",c.nome),el("span",i===estado.ordem?(estado.direcao===1?"↑":"↓"):"↕","seta"));
        bt.setAttribute("aria-label","Ordenar por "+c.nome);
        bt.addEventListener("click",()=>{if(estado.ordem===i) estado.direcao*=-1;else{estado.ordem=i;estado.direcao=1;}estado.pagina=0;desenhar();});
        th.append(bt);tr.append(th);
      });
      head.append(tr);table.append(head);const body=el("tbody");
      if(!visiveis.length){const row=el("tr"),td=el("td","Nenhum registro corresponde aos filtros.","vazio");td.colSpan=colunas.length;row.append(td);body.append(row);}
      for(const r of visiveis.slice(inicio,fim)){
        const row=el("tr");
        colunas.forEach((c,i)=>{
          const v=r[i], td=el("td");
          if(v===null || v===undefined)td.textContent="—";
          else if(c.tipo==="status")td.append(el("span",nomesStatus[v],"selo "+classesStatus[v]));
          else if(c.tipo==="numero" || c.tipo==="percentual"){
            if(typeof v==="number"){
              td.className="numero";td.textContent=c.tipo==="percentual"?percentual.format(v):numero.format(v);
              td.title=String(v).replace(".",",");
            }else td.textContent=String(v);
          }else if(c.tipo==="data")td.textContent=mes(v);
          else{td.textContent=String(v);if(c.tipo==="wrap")td.className="wrap";}
          row.append(td);
        });body.append(row);
      }
      table.append(body);scroll.append(table);
      const rolagemSuperior=el("div",null,"tabela-scroll-topo");
      rolagemSuperior.tabIndex=0;
      rolagemSuperior.setAttribute("role","region");
      rolagemSuperior.setAttribute("aria-label","Rolagem horizontal superior — "+titulo);
      const pista=el("div",null,"tabela-scroll-pista");
      rolagemSuperior.append(pista);conteudo.append(rolagemSuperior,scroll);
      let esperadoNoTopo=null, esperadoNaTabela=null;
      rolagemSuperior.addEventListener("scroll",()=>{
        const x=rolagemSuperior.scrollLeft;
        if(esperadoNoTopo===x){esperadoNoTopo=null;return;}
        esperadoNoTopo=null;
        if(scroll.scrollLeft!==x){esperadoNaTabela=x;scroll.scrollLeft=x;}
      },{passive:true});
      scroll.addEventListener("scroll",()=>{
        const x=scroll.scrollLeft;
        if(esperadoNaTabela===x){esperadoNaTabela=null;return;}
        esperadoNaTabela=null;
        if(rolagemSuperior.scrollLeft!==x){esperadoNoTopo=x;rolagemSuperior.scrollLeft=x;}
      },{passive:true});
      function ajustarRolagem(){
        if(!scroll.isConnected)return;
        rolagemSuperior.hidden=scroll.scrollWidth<=scroll.clientWidth;
        // Igualar as larguras úteis mantém o mesmo percurso nas duas barras,
        // inclusive quando a tabela também tem uma barra de rolagem vertical.
        rolagemSuperior.style.width=(scroll.clientWidth+2)+"px";
        pista.style.width=scroll.scrollWidth+"px";
        if(rolagemSuperior.scrollLeft!==scroll.scrollLeft){
          esperadoNoTopo=scroll.scrollLeft;rolagemSuperior.scrollLeft=scroll.scrollLeft;
        }
      }
      observadorRolagem=new ResizeObserver(ajustarRolagem);
      observadoresRolagem.add(observadorRolagem);
      observadorRolagem.observe(scroll);observadorRolagem.observe(table);
      requestAnimationFrame(ajustarRolagem);
      const pag=el("div",null,"paginacao");
      const anterior=el("button","Anterior"),proxima=el("button","Próxima");
      anterior.disabled=estado.pagina===0;proxima.disabled=estado.pagina===paginas-1;
      anterior.addEventListener("click",()=>{estado.pagina--;desenhar();});
      proxima.addEventListener("click",()=>{estado.pagina++;desenhar();});
      pag.append(anterior,el("span",`Página ${estado.pagina+1} de ${paginas}`),proxima);conteudo.append(pag);
    }
    desenhar();$("conteudo").append(painel);
  }

  function mostrarGeral(){
    const porTipo=new Map(),porUsina=new Map(),porData=new Map(),total=resumo();
    for(const p of pares){
      if(!porUsina.has(p[0]))porUsina.set(p[0],resumo());
      if(!porData.has(p[1]))porData.set(p[1],resumo());
      const u=porUsina.get(p[0]),d=porData.get(p[1]);u.pares++;d.pares++;total.pares++;
      camposAtivos(p,(i,s)=>{
        const tipo=indices[i].lag?"Coeficientes mensais":D.nomes_campos[i];
        if(!porTipo.has(tipo))porTipo.set(tipo,resumo());
        [porTipo.get(tipo),u,d,total].forEach(r=>somar(r,s));
      });
    }
    tabela("total","Resumo do intervalo","Contagens de parâmetros. sc não entra no percentual de comparações dentro da tolerância.",
      [col("Usinas","numero"),col("Meses","numero"),col("Combinações usina–mês","numero"),...colsResumo],
      [[porUsina.size,porData.size,total.pares,...valoresResumo(total)]]);
    tabela("tipos","Resumo por tipo de parâmetro","Todas as usinas e datas abrangidas pelos filtros.",
      [col("Tipo de parâmetro"),...colsResumo],Array.from(porTipo,([t,r])=>[t,...valoresResumo(r)]));
    tabela("usinas","Resumo por usina","Classificação inicial: maior número de parâmetros fora da tolerância. Clique nas colunas para mudar a ordem.",
      [col("Usina"),col("Combinações usina–mês","numero"),...colsResumo],
      Array.from(porUsina,([i,r])=>[D.usinas[i][0],r.pares,...valoresResumo(r)]),4,-1);
    tabela("meses","Resumo por mês e ano","Comparações dos parâmetros de todas as usinas no respectivo mês e ano.",
      [col("Mês/ano","data"),col("Combinações usina–mês","numero"),...colsResumo],
      Array.from(porData,([i,r])=>[D.datas[i],r.pares,...valoresResumo(r)]));
    tabela("precisao","Tolerâncias utilizadas","Critérios escolhidos antes da geração. Coeficientes usam limites globais; médias e desvios usam o percentual indicado por usina e estágio. Os critérios não mudam com os filtros.",
      [col("Tipo de parâmetro"),col("Tolerância absoluta","numero"),col("Unidade"),col("Precisão de origem","wrap")],D.precisao);
    tabela("fontes","Fontes do relatório","Identificação dos parquets completos usados nesta geração. As contagens abaixo não mudam com os filtros.",
      [col("Modelo"),col("Parquet de origem","wrap"),col("Registros conferidos","numero"),col("Usinas","numero"),col("Meses","numero"),col("Combinações usina–mês","numero")],
      D.fontes.map(f=>[f.modelo,f.caminho,f.registros,f.usinas,f.meses,f.pares]));
  }

  function mostrarDetalhe(){
    let campos;
    if(aba==="ordem")campos=indices.filter(x=>x.campo==="ar_order");
    else if(aba==="mensais")campos=indices.filter(x=>x.lag);
    else if(aba==="anual")campos=indices.filter(x=>x.campo==="annual_coefficient");
    else campos=indices.filter(x=>x.campo.endsWith("_m3s"));
    const colunas=[col("Usina"),col("Mês/ano","data")];
    if(aba==="mensais")colunas.push(col("Lag","numero"));
    if(aba==="estatisticas")colunas.push(col("Parâmetro"));
    colunas.push(col("Novo modelo","numero"),col("NEWAVE","numero"),col("Diferença absoluta","numero"),col("Tolerância","numero"),col("Resultado","status"),col("Unidade"));
    if(aba==="mensais")colunas.push(col("Motivo de sc","wrap"),col("Ordem novo modelo","numero"),col("Ordem NEWAVE","numero"));
    const linhas=[];
    for(const p of pares)for(const {campo,i,lag} of campos){
      const a=p[4][i], b=p[5][i];if(lag && a===null && b===null)continue;
      const r=[D.usinas[p[0]][0],D.datas[p[1]]];
      if(aba==="mensais")r.push(Number(campo.split("_").at(-1)));
      if(aba==="estatisticas")r.push(D.nomes_campos[i]);
      r.push(a,b,p[6][i],p[8]?.[i]??D.tolerancias[i],p[7][i],campo.endsWith("_m3s")?"m³/s":"Adimensional");
      if(aba==="mensais")r.push(p[7][i]!==2?"":a===null?`Lag não ativo no novo modelo (p=${p[4][0]})`:`Lag não ativo no NEWAVE (p=${p[5][0]})`,p[4][0],p[5][0]);
      linhas.push(r);
    }
    tabela(aba,tabNames[aba],"Valores armazenados nos parquets, associados pela usina e pelo mês/ano. Diferença absoluta = |novo modelo − NEWAVE|.",colunas,linhas,0,1,true);
  }

  function render(){
    for(const observador of observadoresRolagem)observador.disconnect();
    observadoresRolagem.clear();
    $("conteudo").replaceChildren();
    $("conteudo").setAttribute("aria-labelledby","aba-"+aba);
    if(aba==="geral")mostrarGeral();else mostrarDetalhe();
  }
  function filtrar(){
    const busca=normalizar($("busca").value), inicio=Number($("inicio").value), fim=Number($("fim").value);
    const buscaId=/^\d+$/.test($("busca").value.trim());
    const usinasPermitidas=new Set(D.usinas.map((u,i)=>[u,i]).filter(([u])=>!busca ||
      (buscaId ? u[1]===Number(busca)||u[2]===Number(busca) : normalizar(u[0]).includes(busca))).map(([,i])=>i));
    pares=D.linhas.filter(p=>usinasPermitidas.has(p[0])&&p[1]>=inicio&&p[1]<=fim);
    for(const e of estados.values())e.pagina=0;
    const n=new Set(pares.map(p=>p[0])).size;
    $("escopo").textContent=`${n} usina(s) · ${pares.length} combinação(ões) usina–mês · ${mes(D.datas[inicio])} a ${mes(D.datas[fim])}. Busca e datas valem para todas as abas.`;
    render();
  }
  function mudarAba(nome){
    aba=nome;
    document.querySelectorAll("[data-tab]").forEach(bt=>{const ativa=bt.dataset.tab===aba;bt.setAttribute("aria-selected",String(ativa));bt.tabIndex=ativa?0:-1;});
    render();
  }
  document.querySelectorAll("[data-tab]").forEach(bt=>{
    bt.addEventListener("click",()=>mudarAba(bt.dataset.tab));
    bt.addEventListener("keydown",e=>{
      const botoes=Array.from(document.querySelectorAll("[data-tab]"));let i=botoes.indexOf(bt);
      if(e.key==="ArrowRight")i=(i+1)%botoes.length;else if(e.key==="ArrowLeft")i=(i-1+botoes.length)%botoes.length;else if(e.key==="Home")i=0;else if(e.key==="End")i=botoes.length-1;else return;
      e.preventDefault();mudarAba(botoes[i].dataset.tab);botoes[i].focus();
    });
  });
  opcoes($("inicio"),D.datas.map((d,i)=>[i,mes(d)]));opcoes($("fim"),D.datas.map((d,i)=>[i,mes(d)]));
  $("fim").value=D.datas.length-1;
  $("busca").addEventListener("input",()=>{clearTimeout(atrasoBusca);atrasoBusca=setTimeout(filtrar,180);});
  $("inicio").addEventListener("change",()=>{if(Number($("inicio").value)>Number($("fim").value))$("fim").value=$("inicio").value;filtrar();});
  $("fim").addEventListener("change",()=>{if(Number($("fim").value)<Number($("inicio").value))$("inicio").value=$("fim").value;filtrar();});
  $("limpar").addEventListener("click",()=>{clearTimeout(atrasoBusca);$("busca").value="";$("inicio").value=0;$("fim").value=D.datas.length-1;for(const e of estados.values())e.status="todos";filtrar();});
  $("identificacao").textContent=`${D.usinas.length} usinas · ${D.datas.length} meses · ${mes(D.datas[0])} a ${mes(D.datas.at(-1))} · relatório completo e independente`;
  const percentualEstatisticas=D.percentual_estatisticas;
  if(Number.isFinite(percentualEstatisticas)){
    $("configuracao-tolerancias").hidden=false;
    $("configuracao-tolerancias").textContent=`Médias e desvios padrão: tolerância de ${numero.format(percentualEstatisticas)}% × |NEWAVE|, calculada por usina e estágio. NEWAVE igual a zero implica tolerância zero.`;
    $("metodo-tolerancias").textContent=`Nos coeficientes mensais e no anual, as tolerâncias são globais por tipo e usam a unidade inteira de precisão do valor menos preciso. Nas médias e desvios, a tolerância é ${numero.format(percentualEstatisticas)}% de |NEWAVE| para cada usina e estágio, com o percentual escolhido antes da geração. NEWAVE zero implica tolerância zero. Busca e datas não recalculam esses limites.`;
  }else{
    $("metodo-tolerancias").textContent="Este relatório utiliza as tolerâncias fixas registradas na sua geração, exibidas na Visão geral. Gere um novo relatório pelo programa para escolher o percentual das médias e desvios padrão.";
  }
  $("rodape").textContent="Gerado em "+new Date(D.gerado_em).toLocaleString("pt-BR")+" · Comparador de parâmetros · Dados incorporados neste arquivo · Nenhum dado é enviado pela página.";
  filtrar();
})();
