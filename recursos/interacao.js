"use strict";
(() => {
  const D = JSON.parse(document.getElementById("dados").textContent);
  const $ = id => document.getElementById(id);
  const [nomeA,nomeB]=D.rotulos_modelos||["Novo modelo","NEWAVE"];
  const titulo=nomeA+" × "+nomeB;
  document.title="Comparação de parâmetros — "+titulo;
  document.querySelector("h1").textContent=titulo;
  const numero = new Intl.NumberFormat("pt-BR", {useGrouping:false, maximumSignificantDigits:15});
  const percentual = new Intl.NumberFormat("pt-BR", {useGrouping:false, minimumFractionDigits:2, maximumFractionDigits:2});
  const nomesMeses = ["Janeiro","Fevereiro","Março","Abril","Maio","Junho","Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"];
  const mes = d => d.slice(5,7) + "/" + d.slice(0,4);
  const normalizar = s => String(s).normalize("NFD").replace(/[\u0300-\u036f]/g, "").toUpperCase().replace(/[^A-Z0-9]/g, "");
  const nomesStatus = ["Dentro da tolerância", "Fora da tolerância", "sc"];
  const classesStatus = ["dentro", "fora", "sc"];
  const tabNames = {geral:"Visão geral", ordem:"Ordem PARP", mensais:"Coeficientes mensais", anual:"Coeficiente anual",
    medias_mensais:"Médias mensais",medias_anuais:"Médias anuais",desvio_mensal:"Desvio padrão mensal",desvio_anual:"Desvio padrão anual"};
  const camposPorAba={ordem:"ar_order",anual:"annual_coefficient",medias_mensais:"seasonal_mean_m3s",
    medias_anuais:"annual_mean_m3s",desvio_mensal:"seasonal_std_m3s",desvio_anual:"annual_std_m3s"};
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
    const n = r.dentro + r.fora + r.sc;
    return [n, r.dentro, r.fora+r.sc, n ? 100*r.dentro/n : null];
  }
  const col = (nome,tipo="texto") => ({nome,tipo});
  const colsResumo = [col("Avaliados","numero"),col("Aprovados","numero"),col("Reprovados (fora + sc)","numero"),col("Aprovação (%)","percentual")];

  function comparar(a,b,tipo,direcao) {
    if (a === null || a === undefined) return b === null || b === undefined ? 0 : 1;
    if (b === null || b === undefined) return -1;
    let v;
    if (["numero","percentual","status","mes"].includes(tipo) && typeof a==="number" && typeof b==="number") v = a-b;
    else v = String(a).localeCompare(String(b),"pt-BR",{numeric:true,sensitivity:"base"});
    return v*direcao;
  }
  const chaveValor = v => JSON.stringify(v ?? null);
  const textoFiltro = v => String(v).normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLocaleLowerCase("pt-BR");
  const numeroFiltro = v => {
    const texto=String(v).trim().replace(",", ".");
    return /^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?$/i.test(texto) && Number.isFinite(Number(texto)) ? Number(texto) : null;
  };
  function rotuloFiltro(v,c) {
    if(v===null || v===undefined)return "— (sem valor)";
    if(v==="")return "(Texto vazio)";
    if(c.tipo==="status")return nomesStatus[v];
    if(c.tipo==="mes")return nomesMeses[v-1];
    if(c.tipo==="data")return mes(v);
    // Preservar todos os algarismos nas opções: dois doubles próximos não se fundem.
    return typeof v==="number" ? String(v).replace(".",",") : String(v);
  }
  function atendeFiltro(v,c,f,selecionados=null) {
    if(f.valores!==null && !(selecionados || new Set(f.valores)).has(chaveValor(v)))return false;
    if(f.operador==="todos")return true;
    if(c.tipo==="numero" || c.tipo==="percentual"){
      if(typeof v!=="number")return false;
      const x=numeroFiltro(f.valor), y=numeroFiltro(f.ate);
      if(x===null)return false;
      switch(f.operador){
        case "igual":return v===x;
        case "diferente":return v!==x;
        case "maior":return v>x;
        case "maior_igual":return v>=x;
        case "menor":return v<x;
        case "menor_igual":return v<=x;
        case "entre":return y!==null && v>=x && v<=y;
      }
    }
    const texto=textoFiltro(v??""), busca=textoFiltro(f.valor);
    switch(f.operador){
      case "contem":return texto.includes(busca);
      case "nao_contem":return !texto.includes(busca);
      case "igual":return texto===busca;
      case "diferente":return texto!==busca;
      case "comeca":return texto.startsWith(busca);
      case "termina":return texto.endsWith(busca);
    }
    return false;
  }
  function menuFiltro(botao,c,indice,linhas,estado,aplicar) {
    const atual=estado.filtros[indice] || {valores:null,operador:"todos",valor:"",ate:""};
    const valores=new Map(linhas.map(r=>[chaveValor(r[indice]),r[indice]]));
    for(const chave of atual.valores || [])if(!valores.has(chave))valores.set(chave,JSON.parse(chave));
    const opcoesValores=Array.from(valores,([chave,valor])=>({chave,valor,rotulo:rotuloFiltro(valor,c)}))
      .sort((a,b)=>comparar(a.valor,b.valor,c.tipo,1));
    const selecionados=new Set(atual.valores===null ? valores.keys() : atual.valores);
    const dialog=el("dialog",null,"filtro-coluna-dialog");
    const cabecalho=el("div",null,"filtro-coluna-titulo");
    const titulo=el("strong","Filtrar: "+c.nome),fechar=el("button","×","filtro-fechar");
    fechar.type="button";fechar.setAttribute("aria-label","Fechar filtro");
    cabecalho.append(titulo,fechar);dialog.append(cabecalho);
    dialog.setAttribute("aria-label","Filtro da coluna "+c.nome);
    const nota=el("p","Combine colunas para restringir as linhas desta tabela. As opções incluem todas as páginas do recorte geral.","filtro-ajuda");
    dialog.append(nota);
    const numerica=["numero","percentual"].includes(c.tipo);
    const condicao=el("select");condicao.setAttribute("aria-label","Condição da coluna "+c.nome);
    const condicoes=numerica ? [["todos","Sem condição numérica"],["igual","Igual a"],["diferente","Diferente de"],["maior","Maior que"],["maior_igual","Maior ou igual a"],["menor","Menor que"],["menor_igual","Menor ou igual a"],["entre","Entre (inclusive)"]]
      : [["todos","Sem condição de texto"],["contem","Contém"],["nao_contem","Não contém"],["igual","Igual a"],["diferente","Diferente de"],["comeca","Começa com"],["termina","Termina com"]];
    const permiteCondicao=numerica || ["texto","wrap"].includes(c.tipo);
    opcoes(condicao,condicoes);condicao.value=atual.operador;
    const entradas=el("div",null,"filtro-condicao");
    const valor=el("input"),ate=el("input");
    valor.type=ate.type="text";valor.value=atual.valor;ate.value=atual.ate;
    valor.setAttribute("aria-label","Valor da condição");ate.setAttribute("aria-label","Limite superior");
    valor.placeholder=numerica ? "Ex.: -0,1 ou 1e-3" : "Texto";ate.placeholder="Até (inclusive)";
    entradas.append(valor,ate);
    function ajustarCondicao(){entradas.hidden=condicao.value==="todos";ate.hidden=condicao.value!=="entre";valor.setCustomValidity("");ate.setCustomValidity("");if(dialog.open)requestAnimationFrame(posicionar);}
    if(permiteCondicao)dialog.append(condicao,entradas);
    condicao.addEventListener("change",ajustarCondicao);ajustarCondicao();
    [valor,ate].forEach(e=>e.addEventListener("input",()=>e.setCustomValidity("")));
    const busca=el("input");busca.type="search";busca.placeholder="Buscar valores na lista";
    busca.setAttribute("aria-label","Buscar valores da coluna "+c.nome);dialog.append(busca);
    const todosLabel=el("label",null,"filtro-opcao filtro-todos"),todos=el("input");todos.type="checkbox";
    todos.setAttribute("aria-label","Selecionar todos os resultados da busca");
    todosLabel.append(todos,el("span","Selecionar todos os resultados da busca"));dialog.append(todosLabel);
    const selecao=el("div",null,"filtro-selecao"),somente=el("button","Somente resultados da busca","filtro-mais"),nenhum=el("button","Desmarcar todos","filtro-mais");
    somente.type=nenhum.type="button";selecao.append(somente,nenhum);dialog.append(selecao);
    const lista=el("div",null,"filtro-valores");lista.setAttribute("role","group");lista.setAttribute("aria-label","Valores disponíveis");dialog.append(lista);
    const info=el("p",null,"filtro-ajuda");info.setAttribute("role","status");dialog.append(info);
    let limite=100;
    const encontradas=()=>{
      const consulta=textoFiltro(busca.value);
      return opcoesValores.filter(o=>textoFiltro(o.rotulo).includes(consulta))
        .sort((a,b)=>Number(textoFiltro(b.rotulo)===consulta)-Number(textoFiltro(a.rotulo)===consulta));
    };
    function atualizarSelecao(){
      const opcoes=encontradas(),n=opcoes.filter(o=>selecionados.has(o.chave)).length;
      todos.checked=opcoes.length>0 && n===opcoes.length;
      todos.indeterminate=n>0 && n<opcoes.length;todos.disabled=!opcoes.length;
      info.textContent=`${selecionados.size} de ${opcoesValores.length} valores selecionados · ${opcoes.length} encontrados. A busca apenas localiza opções.`;
    }
    function desenharLista(){
      lista.replaceChildren();const opcoes=encontradas();
      if(!opcoes.length)lista.append(el("p","Nenhum valor encontrado.","filtro-ajuda"));
      for(const o of opcoes.slice(0,limite)){
        const label=el("label",null,"filtro-opcao"),check=el("input");check.type="checkbox";check.checked=selecionados.has(o.chave);check.dataset.valor=o.chave;
        const texto=el("span",o.rotulo);texto.title=o.rotulo;label.append(check,texto);
        check.addEventListener("change",()=>{if(check.checked)selecionados.add(o.chave);else selecionados.delete(o.chave);atualizarSelecao();});
        lista.append(label);
      }
      if(opcoes.length>limite){const mais=el("button",`Mostrar mais (${opcoes.length-limite} restantes)`,"filtro-mais");mais.type="button";mais.addEventListener("click",()=>{limite+=100;desenharLista();});lista.append(mais);}
      atualizarSelecao();
    }
    busca.addEventListener("input",()=>{limite=100;desenharLista();});
    somente.addEventListener("click",()=>{selecionados.clear();for(const o of encontradas())selecionados.add(o.chave);desenharLista();});
    nenhum.addEventListener("click",()=>{selecionados.clear();desenharLista();});
    todos.addEventListener("change",()=>{for(const o of encontradas()){if(todos.checked)selecionados.add(o.chave);else selecionados.delete(o.chave);}desenharLista();});
    desenharLista();
    const acoes=el("div",null,"filtro-acoes"),limpar=el("button","Limpar coluna","secundario"),cancelar=el("button","Cancelar","secundario"),ok=el("button","Aplicar","filtro-aplicar");
    for(const bt of [limpar,cancelar,ok])bt.type="button";
    acoes.append(limpar,cancelar,ok);dialog.append(acoes);
    function concluir(filtro){
      if(filtro && (filtro.valores!==null || filtro.operador!=="todos"))estado.filtros[indice]=filtro;
      else delete estado.filtros[indice];
      dialog.close();estado.pagina=0;aplicar();
      requestAnimationFrame(()=>document.querySelector(`[data-table="${aba}"] [data-filtro-coluna="${indice}"]`)?.focus());
    }
    limpar.addEventListener("click",()=>concluir(null));cancelar.addEventListener("click",()=>dialog.close());fechar.addEventListener("click",()=>dialog.close());
    ok.addEventListener("click",()=>{
      if(numerica && condicao.value!=="todos"){
        if(numeroFiltro(valor.value)===null){valor.setCustomValidity("Informe um número válido, com ponto ou vírgula decimal.");valor.reportValidity();return;}
        if(condicao.value==="entre" && (numeroFiltro(ate.value)===null || numeroFiltro(ate.value)<numeroFiltro(valor.value))){ate.setCustomValidity("Informe um limite superior válido, maior ou igual ao primeiro valor.");ate.reportValidity();return;}
      }
      concluir({valores:opcoesValores.every(o=>selecionados.has(o.chave)) ? null : Array.from(selecionados),operador:condicao.value,valor:valor.value,ate:ate.value});
    });
    dialog.addEventListener("click",e=>{const r=dialog.getBoundingClientRect();if(e.target===dialog && (e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom))dialog.close();});
    function posicionar(){
      const r=botao.getBoundingClientRect(),margem=12;
      dialog.style.left=Math.max(margem,Math.min(r.right-dialog.offsetWidth,window.innerWidth-dialog.offsetWidth-margem))+"px";
      dialog.style.top=Math.max(margem,Math.min(r.bottom+5,window.innerHeight-dialog.offsetHeight-margem))+"px";
    }
    dialog.addEventListener("close",()=>{window.removeEventListener("resize",posicionar);dialog.remove();if(botao.isConnected)botao.focus();},{once:true});
    document.body.append(dialog);dialog.showModal();posicionar();window.addEventListener("resize",posicionar);busca.focus();
  }
  function criarIndicadores(linhas,statusCol,id) {
    const combinacoes=new Set(),reprovadas=new Set(),usinas=new Set(),usinasReprovadas=new Set(),combinacoesComparaveis=new Set(),usinasComparaveis=new Set();
    let dentro=0,fora=0,sc=0;
    for(const r of linhas){
      const chave=JSON.stringify([r[0],r[1]]),status=r[statusCol];
      combinacoes.add(chave);usinas.add(r[0]);
      if(status===2)sc++;
      else{combinacoesComparaveis.add(chave);usinasComparaveis.add(r[0]);}
      if(status===0)dentro++;
      else{if(status===1)fora++;reprovadas.add(chave);usinasReprovadas.add(r[0]);}
    }
    const comparaveis=dentro+fora,avaliados=comparaveis+sc,reprovados=fora+sc;
    const taxa=avaliados ? 100*reprovados/avaliados : null,taxaAprovacao=avaliados ? 100*dentro/avaliados : null;
    const tipo=id==="ordem" ? "Ordens" : id.startsWith("medias_") ? "Médias" : id.startsWith("desvio_") ? "Desvios" : ["mensais","anual"].includes(id) ? "Coeficientes" : "Parâmetros";
    const flexao=id==="ordem" || id.startsWith("medias_") ? "as" : "os";
    const dados=[
      ["combinacoes","Combinações usina–mês no recorte",combinacoes.size,`${numero.format(combinacoesComparaveis.size)} com comparação efetiva`,"neutro"],
      ["usinas","Usinas no recorte",usinas.size,`${numero.format(usinasComparaveis.size)} com comparação efetiva`,"neutro"],
      ["avaliados",tipo+" avaliad"+flexao,avaliados,"Aprovados + reprovados (sc incluído)","neutro"],
      ["sc","Sem comparação (sc)",sc,"Já incluídos nos reprovados","sc"],
      ["combinacoes_aprovadas","Combinações usina–mês aprovadas",combinacoes.size-reprovadas.size,"Todas as grandezas aprovadas; nenhum sc no recorte","aprovacao"],
      ["usinas_aprovadas","Usinas aprovadas no recorte",usinas.size-usinasReprovadas.size,"Nenhuma reprovação ou sc no recorte","aprovacao"],
      ["aprovados",tipo+" aprovad"+flexao,dentro,"Somente dentro da tolerância","aprovacao"],
      ["taxa_aprovacao","Taxa de aprovação",taxaAprovacao,`${numero.format(dentro)} aprovad${flexao} / ${numero.format(avaliados)} avaliados · sc incluído`,"aprovacao"],
      ["combinacoes_reprovadas","Combinações usina–mês reprovadas",reprovadas.size,"Ao menos uma grandeza fora da tolerância ou sc","reprovacao"],
      ["usinas_reprovadas","Usinas com ao menos um mês reprovado",usinasReprovadas.size,"Cada usina é contada uma única vez","reprovacao"],
      ["reprovados",tipo+" reprovad"+flexao,reprovados,id==="mensais" ? `${numero.format(fora)} fora da tolerância + ${numero.format(sc)} sem comparação` : "Fora da tolerância + sem comparação","reprovacao"],
      ["taxa_reprovacao","Taxa de reprovação",taxa,`${numero.format(reprovados)} reprovad${flexao} / ${numero.format(avaliados)} avaliados · sc incluído`,"taxa"]
    ];
    const secao=el("section",null,"indicadores");secao.setAttribute("aria-label","Indicadores — "+(tabNames[id]||"Visão geral"));
    const temCombinacoes=id==="geral" || id==="mensais";
    const grade=el("div",null,"indicadores-grade"+(temCombinacoes ? "" : " indicadores-sem-combinacoes"));
    for(const [chave,titulo,valor,detalhe,estilo] of dados){
      if(chave==="sc" && id!=="mensais")continue;
      if(chave.startsWith("combinacoes") && !temCombinacoes)continue;
      let destaque="";
      if(estilo==="sc")destaque=" indicador-sc";
      else if(valor>0){
        if(estilo==="aprovacao")destaque=" indicador-aprovacao";
        else if(estilo==="reprovacao"||estilo==="taxa")destaque=" indicador-reprovacao";
      }
      const card=el("article",null,"indicador"+destaque);
      card.dataset.indicador=chave;
      card.append(el("p",titulo,"indicador-titulo"),
        el("p",valor===null ? "—" : chave.startsWith("taxa_") ? percentual.format(valor)+"%" : numero.format(valor),"indicador-valor"),
        el("p",valor===null ? "Sem linhas no recorte" : detalhe,"indicador-detalhe"));
      grade.append(card);
    }
    secao.append(grade,el("p",id==="geral"
      ? "Indicadores do recorte geral. Reprovados = fora da tolerância + sem comparação. As taxas usam todos os avaliados, inclusive sc."
      : "Base: todas as linhas após os filtros ativos, antes da paginação. O cartão de reprovados reúne fora da tolerância e sem comparação (sc); taxas calculadas sobre todos os avaliados. Uma combinação ou usina com sc é reprovada.","indicadores-base"));
    return secao;
  }
  function tabela(id, titulo, descricao, colunas, linhas, ordem=0, direcao=1, filtrarStatus=false) {
    let estado = estados.get(id);
    if (!estado) { estado={ordem,direcao,pagina:0,tamanho:100,status:"todos",filtros:{}}; estados.set(id,estado); }
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
        opcoes(filtro,[["todos","Todos"],["0",nomesStatus[0]],["reprovados","Reprovados (fora + sc)"],["1",nomesStatus[1]],["2","sc — reprovado sem comparação"]]);
        filtro.value=estado.status;
        filtro.addEventListener("change",()=>{estado.status=filtro.value;estado.pagina=0;desenhar();});
        label.append(filtro);toolbar.append(label);
        const limpar=el("button","Limpar filtros desta tabela","secundario");limpar.type="button";
        limpar.disabled=estado.status==="todos" && !Object.keys(estado.filtros).length;
        limpar.addEventListener("click",()=>{estado.status="todos";estado.filtros={};estado.pagina=0;desenhar();});
        toolbar.append(limpar);
        const n=Object.keys(estado.filtros).length;
        if(n)toolbar.append(el("span",`${n} coluna(s) com filtro ativo`,"filtro-indicador"));
      }
      const statusCol = colunas.findIndex(c=>c.tipo==="status");
      const filtrosAtivos=Object.entries(estado.filtros).map(([i,f])=>[i,f,f.valores===null ? null : new Set(f.valores)]);
      const visiveis = linhas.filter(r=>(estado.status==="todos" || statusCol<0 || (estado.status==="reprovados" ? r[statusCol]!==0 : r[statusCol]===Number(estado.status))) &&
        filtrosAtivos.every(([i,f,s])=>atendeFiltro(r[i],colunas[i],f,s)));
      if(filtrarStatus)conteudo.append(criarIndicadores(visiveis,statusCol,id));
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
        const cabecalho=el("div",null,"cabecalho-coluna");cabecalho.append(bt);
        if(filtrarStatus){
          const filtro=el("button","▾","botao-filtro"+(estado.filtros[i]?" ativo":""));filtro.type="button";
          filtro.dataset.filtroColuna=i;filtro.setAttribute("aria-label","Filtrar coluna "+c.nome);
          filtro.setAttribute("aria-haspopup","dialog");filtro.title="Filtrar "+c.nome+(estado.filtros[i]?" — filtro ativo":"");
          filtro.addEventListener("click",()=>menuFiltro(filtro,c,i,linhas,estado,desenhar));cabecalho.append(filtro);
        }
        th.append(cabecalho);tr.append(th);
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
          }else if(c.tipo==="mes")td.textContent=nomesMeses[v-1];
          else if(c.tipo==="data")td.textContent=mes(v);
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
    const porTipo=new Map(),porUsina=new Map(),porData=new Map();
    for(const p of pares){
      if(!porUsina.has(p[0]))porUsina.set(p[0],resumo());
      if(!porData.has(p[1]))porData.set(p[1],resumo());
      const u=porUsina.get(p[0]),d=porData.get(p[1]);u.pares++;d.pares++;
      camposAtivos(p,(i,s)=>{
        const tipo=indices[i].lag?"Coeficientes mensais":D.nomes_campos[i];
        if(!porTipo.has(tipo))porTipo.set(tipo,resumo());
        [porTipo.get(tipo),u,d].forEach(r=>somar(r,s));
      });
    }
    tabela("tipos","Resumo por tipo de parâmetro","Todas as usinas e datas abrangidas pelos filtros.",
      [col("Tipo de parâmetro"),...colsResumo],Array.from(porTipo,([t,r])=>[t,...valoresResumo(r)]));
    tabela("usinas","Resumo por usina","Classificação inicial: maior número de reprovados (fora da tolerância + sc). Clique nas colunas para mudar a ordem.",
      [col("Usina"),col("Combinações usina–mês","numero"),...colsResumo],
      Array.from(porUsina,([i,r])=>[D.usinas[i][0],r.pares,...valoresResumo(r)]),4,-1);
    tabela("meses","Resumo por mês do ano","Comparações de todas as grandezas, uma vez por usina e mês do ano. Todos os anos foram validados antes da consolidação.",
      [col("Mês do ano","mes"),col("Combinações usina–mês","numero"),...colsResumo],
      Array.from(porData,([i,r])=>[D.meses[i],r.pares,...valoresResumo(r)]));
    tabela("fontes","Fontes do relatório","Identificação dos parquets completos usados nesta geração. As contagens abaixo não mudam com os filtros.",
      [col("Modelo"),col("Parquet de origem","wrap"),col("Registros conferidos","numero"),col("Usinas","numero"),col("Meses no horizonte","numero"),col("Pares usina–mês/ano conferidos","numero"),col("Conjuntos mensais","numero"),col("Verificação entre anos","wrap")],
      D.fontes.map(f=>{const v=f.validacao_mensal;return [f.rotulo||f.modelo,f.caminho,f.registros,f.usinas,f.meses,f.pares,v.conjuntos,`Igualdade exata confirmada em ${v.grupos_com_repeticao} grupo(s); ${v.grupos_sem_repeticao} grupo(s) com um único ano, sem repetição a conferir.`];}));
  }

  function mostrarDetalhe(){
    const campos=indices.filter(x=>aba==="mensais" ? x.lag : x.campo===camposPorAba[aba]);
    const colunas=[col("Usina"),col("Mês do ano","mes")];
    if(aba==="mensais")colunas.push(col("Lag","numero"));
    colunas.push(col(nomeA,"numero"),col(nomeB,"numero"),col("Diferença absoluta","numero"),col("Tolerância","numero"),col("Resultado","status"),col("Unidade"));
    if(aba==="mensais")colunas.push(col("Motivo de sc","wrap"),col("Ordem "+nomeA,"numero"),col("Ordem "+nomeB,"numero"));
    const linhas=[];
    for(const p of pares)for(const {campo,i,lag} of campos){
      const a=p[4][i], b=p[5][i];if(lag && a===null && b===null)continue;
      const r=[D.usinas[p[0]][0],D.meses[p[1]]];
      if(aba==="mensais")r.push(Number(campo.split("_").at(-1)));
      r.push(a,b,p[6][i],p[8] ? p[8][i] : D.tolerancias[i],p[7][i],campo.endsWith("_m3s")?"m³/s":"Adimensional");
      if(aba==="mensais")r.push(p[7][i]!==2?"":p[4][0]!==p[5][0]
        ? `Ordens diferentes: ${nomeA} (p=${p[4][0]}) e ${nomeB} (p=${p[5][0]})`
        : a===null?`Lag não ativo em ${nomeA} (p=${p[4][0]})`:`Lag não ativo em ${nomeB} (p=${p[5][0]})`,p[4][0],p[5][0]);
      linhas.push(r);
    }
    const grandeza=aba==="mensais" ? "Coeficientes autorregressivos por lag." : D.nomes_campos[campos[0].i]+".";
    tabela(aba,tabNames[aba],`${grandeza} Valores armazenados nos parquets, associados pela usina e pelo mês do ano, após validar todos os anos. Cada conjunto mensal aparece uma única vez. Diferença absoluta = |${nomeA} − ${nomeB}|. Use ▾ nos cabeçalhos para combinar filtros nesta tabela.`,colunas,linhas,0,1,true);
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
    const mesesPermitidos=new Set(D.datas.slice(inicio,fim+1).map(d=>Number(d.slice(5,7))));
    pares=D.linhas.filter(p=>usinasPermitidas.has(p[0])&&mesesPermitidos.has(D.meses[p[1]]));
    for(const e of estados.values())e.pagina=0;
    const n=new Set(pares.map(p=>p[0])).size;
    $("escopo").textContent=`${n} usina(s) · ${pares.length} combinação(ões) usina–mês · ${mes(D.datas[inicio])} a ${mes(D.datas[fim])}. Meses contados uma única vez; busca e intervalo valem para todas as abas.`;
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
  $("limpar").addEventListener("click",()=>{clearTimeout(atrasoBusca);$("busca").value="";$("inicio").value=0;$("fim").value=D.datas.length-1;for(const e of estados.values()){e.status="todos";e.filtros={};}filtrar();});
  $("identificacao").textContent=`${D.usinas.length} usinas · ${D.meses.length} meses do ano comparados · ${D.datas.length} meses no horizonte · ${mes(D.datas[0])} a ${mes(D.datas.at(-1))} · relatório completo e independente`;
  $("rodape").textContent="Gerado em "+new Date(D.gerado_em).toLocaleString("pt-BR")+" · Comparador de parâmetros · Dados incorporados neste arquivo · Nenhum dado é enviado pela página.";
  filtrar();
})();
