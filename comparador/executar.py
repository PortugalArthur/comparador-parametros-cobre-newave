"""Entrada gráfica pelo BAT e entrada reproduzível por linha de comando."""

import argparse
from datetime import datetime
import json
from pathlib import Path
import queue
import sys
import threading
import webbrowser

from infraestrutura.preparar_ambiente import garantir_dependencias


RAIZ = Path(__file__).resolve().parents[1]


def gerar(novo, newave, deck, saida=None, deck_newave=None, progresso=print, *,
          tipo_comparacao="novo_newave", deck_referencia=None, rotulo_novo=None, rotulo_referencia=None):
    from .dados import conferir_deck_newave, ErroConsistencia, ler_fonte
    from .regras import comparar
    from .relatorio import salvar_html

    if tipo_comparacao not in ("novo_newave", "novo_novo"):
        raise ErroConsistencia("Tipo de comparação inválido.")
    duas_versoes = tipo_comparacao == "novo_novo"
    if duas_versoes and not deck_referencia:
        raise ErroConsistencia("Selecione o deck correspondente à versão B (referência).")
    if duas_versoes and deck_newave:
        raise ErroConsistencia("O deck NEWAVE não se aplica à comparação de duas versões do novo modelo.")
    rotulos = [rotulo_novo if rotulo_novo is not None else ("Novo modelo A" if duas_versoes else "Novo modelo"),
               rotulo_referencia if rotulo_referencia is not None else ("Novo modelo B" if duas_versoes else "NEWAVE")]
    if any(not isinstance(v, str) or not v.strip() for v in rotulos):
        raise ErroConsistencia("Informe os nomes das duas fontes.")
    rotulos = [v.strip() for v in rotulos]
    if rotulos[0].casefold() == rotulos[1].casefold():
        raise ErroConsistencia("Use nomes diferentes para identificar as duas fontes.")
    novo, newave, deck = (Path(p).resolve() for p in (novo, newave, deck))
    if novo == newave:
        raise ErroConsistencia("Selecione dois parquets distintos.")
    fontes = [novo, newave, deck / "system/hydros.json", deck / "stages.json"]
    if duas_versoes:
        deck_referencia = Path(deck_referencia).resolve()
        fontes.extend([deck_referencia / "system/hydros.json", deck_referencia / "stages.json"])
    if deck_newave:
        fontes.append(Path(deck_newave) / "dger.dat")
    try:
        antes = {p: (p.stat().st_size, p.stat().st_mtime_ns) for p in fontes}
    except OSError as erro:
        raise ErroConsistencia(f"Entrada não encontrada ou inacessível: {erro}") from erro
    if saida is None:
        saida = RAIZ / "relatorios" / ("comparacao_parametros_" + tipo_comparacao + "_" + datetime.now().strftime("%Y%m%d_%H%M%S_%f") + ".html")
    saida = Path(saida).resolve()
    if saida.suffix.lower() != ".html" or saida in fontes:
        raise ErroConsistencia("Escolha um arquivo de saída .html diferente das fontes.")
    a = ler_fonte(novo, "Novo modelo", deck, progresso)
    # O discriminador técnico continua sendo o modelo real, nunca o rótulo de exibição.
    b = ler_fonte(newave, "Novo modelo" if duas_versoes else "NEWAVE",
                  deck_referencia if duas_versoes else None, progresso=progresso)
    if deck_newave:
        conferir_deck_newave(deck_newave, b)
    resultado = comparar(a, b, progresso)
    resultado["tipo_comparacao"] = tipo_comparacao
    resultado["rotulos_modelos"] = rotulos
    resultado["deck_referencia"] = str(deck_referencia) if duas_versoes else None
    if duas_versoes:
        # Apenas descrição: os valores/limites foram produzidos pelas mesmas regras.
        for linha in resultado["precisao"]:
            linha[3] = linha[3].replace("NEWAVE: 3 algarismos significativos; novo modelo: float64 nativo",
                                       "Duas fontes do novo modelo: float64 nativo")
            linha[3] = linha[3].replace("NEWAVE", rotulos[1])
            if isinstance(linha[1], str):
                linha[1] = linha[1].replace("NEWAVE", rotulos[1])
    for fonte, rotulo in zip(resultado["fontes"], rotulos):
        fonte["rotulo"] = rotulo
    resultado["deck_novo_modelo"] = str(deck)
    resultado["deck_newave"] = str(Path(deck_newave).resolve()) if deck_newave else None
    resultado["arquivos_conferidos"] = [dict(caminho=str(p), bytes=tamanho, modificado_ns=tempo)
                                         for p, (tamanho, tempo) in antes.items()]
    for p, assinatura in antes.items():
        if (p.stat().st_size, p.stat().st_mtime_ns) != assinatura:
            raise ErroConsistencia(f"A entrada mudou durante a execução. Repita a comparação: {p}")
    progresso("Gravando o HTML com todas as tabelas...")
    caminho = salvar_html(resultado, saida)
    progresso(f"Relatório concluído: {caminho}")
    return caminho, resultado


def janela():
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    raiz=tk.Tk();raiz.title("Comparador de parâmetros");raiz.geometry("930x850");raiz.minsize(820,780)
    estilo=ttk.Style(raiz);estilo.theme_use("clam")
    estilo.configure("TFrame",background="#f3f6fa")
    estilo.configure("TLabel",background="#f3f6fa",foreground="#102a43",font=("Segoe UI",10))
    estilo.configure("Titulo.TLabel",font=("Segoe UI",19,"bold"),foreground="#154765")
    estilo.configure("TButton",padding=7)
    raiz.configure(background="#f3f6fa")
    painel=ttk.Frame(raiz,padding=24);painel.pack(fill="both",expand=True);painel.columnconfigure(1,weight=1)
    ttk.Label(painel,text="Comparador de parâmetros",style="Titulo.TLabel").grid(row=0,column=0,columnspan=3,sticky="w")
    config=RAIZ/".ultimas_entradas.json"
    try:anterior=json.loads(config.read_text(encoding="utf-8"))
    except (OSError,ValueError):anterior={}
    if not isinstance(anterior,dict):anterior={}
    padroes={"tipo_comparacao":"novo_newave","novo":"","newave":"","deck":"","deck_referencia":"",
             "rotulo_novo":"Novo modelo","rotulo_referencia":"NEWAVE"}
    vs={k:tk.StringVar(value=anterior.get(k,v)) for k,v in padroes.items()}
    tipos={"Novo modelo × NEWAVE":"novo_newave","Novo modelo × Novo modelo":"novo_novo"}
    tipo=tk.StringVar(value=next((k for k,v in tipos.items() if v==vs['tipo_comparacao'].get()),next(iter(tipos))))
    ttk.Label(painel,text="Tipo de comparação").grid(row=1,column=0,sticky="w",pady=12)
    cb=ttk.Combobox(painel,textvariable=tipo,values=list(tipos),state="readonly",width=36);cb.grid(row=1,column=1,columnspan=2,sticky="w")
    widgets=[];arquivo_widgets={};rotulos={}
    for row,key,label in [(2,'novo','Parquet A'),(3,'deck','Deck A'),(4,'newave','Parquet B / referência'),(5,'deck_referencia','Deck B / referência')]:
        lab=ttk.Label(painel,text=label);lab.grid(row=row,column=0,sticky='w',pady=9,padx=(0,10));rotulos[key]=lab
        en=ttk.Entry(painel,textvariable=vs[key],state='readonly');en.grid(row=row,column=1,sticky='ew',padx=(0,8))
        def escolher(k=key):
            base=Path(vs[k].get()).parent if vs[k].get() else RAIZ.parent
            v=(filedialog.askdirectory(parent=raiz,initialdir=base,title='Deck correspondente: system/hydros.json e stages.json') if k.startswith('deck') else
               filedialog.askopenfilename(parent=raiz,initialdir=base,filetypes=[('Parquet','*.parquet')]))
            if v:vs[k].set(v)
        bt=ttk.Button(painel,text='Selecionar…',command=escolher);bt.grid(row=row,column=2)
        arquivo_widgets[key]=(en,bt);widgets.extend([en,bt])
    for row,key,label in [(6,'rotulo_novo','Nome da fonte A'),(7,'rotulo_referencia','Nome da fonte B / referência')]:
        ttk.Label(painel,text=label).grid(row=row,column=0,sticky='w',pady=8)
        en=ttk.Entry(painel,textvariable=vs[key]);en.grid(row=row,column=1,columnspan=2,sticky='ew');widgets.append(en)
    ttk.Label(painel,text='Médias e desvios: tolerância fixa de 0,01 m³/s').grid(row=8,column=0,columnspan=3,sticky='w',pady=10)
    nota=tk.StringVar()
    ttk.Label(painel,textvariable=nota,wraplength=850,justify='left').grid(row=9,column=0,columnspan=3,sticky='w',pady=14)
    ttk.Label(painel,text='Informe as versões nos nomes, por exemplo: Novo modelo 0.19.1 e Novo modelo 0.20.0.\n'
              'As fontes são somente lidas.').grid(row=10,column=0,columnspan=3,sticky='w',pady=8)
    status=tk.StringVar(value='Confira as entradas e gere o HTML.')
    ttk.Label(painel,textvariable=status,wraplength=850).grid(row=11,column=0,columnspan=3,sticky='w',pady=8)
    barra=ttk.Progressbar(painel,mode='indeterminate');barra.grid(row=12,column=0,columnspan=3,sticky='ew',pady=8)
    ocupado=False;fila=queue.Queue()
    def alternar(event=None):
        dupla=tipos[tipo.get()]=='novo_novo'
        if event is not None:
            vs['rotulo_novo'].set('Novo modelo A' if dupla else 'Novo modelo')
            vs['rotulo_referencia'].set('Novo modelo B' if dupla else 'NEWAVE')
            vs['newave'].set('');vs['deck_referencia'].set('')
        vs['tipo_comparacao'].set(tipos[tipo.get()])
        rotulos['novo'].configure(text='Parquet A — novo modelo')
        rotulos['deck'].configure(text='Deck A — novo modelo')
        rotulos['newave'].configure(text='Parquet B — novo modelo' if dupla else 'Parquet B — NEWAVE')
        for w in arquivo_widgets['deck_referencia']:w.configure(state=('readonly' if isinstance(w,ttk.Entry) else 'normal') if dupla else 'disabled')
        nota.set('Médias e desvios mensais e anuais: tolerância absoluta fixa de 0,01 m³/s, inclusive para valores zero.\n'
                 +('Coeficientes: mesma regra de precisão do valor menos preciso, usando float64 das duas fontes; não se aplica a precisão de impressão do NEWAVE.' if dupla else
                   'Coeficientes mensais e anual: 0,001 × 10^e do formato NEWAVE 0.XXXE±YY, individualmente por coeficiente.'))
    cb.bind('<<ComboboxSelected>>',alternar);alternar()
    def iniciar():
        nonlocal ocupado
        if ocupado:return
        args={k:v.get() for k,v in vs.items()}
        if args['tipo_comparacao']=='novo_newave':args['deck_referencia']=None
        ocupado=True;barra.start(12);cb.configure(state='disabled')
        for w in widgets:w.configure(state='disabled')
        bt.configure(state='disabled')
        def worker():
            try:fila.put(('ok',gerar(**args,progresso=lambda t:fila.put(('progresso',t)))))
            except Exception as e:fila.put(('erro',str(e)))
        threading.Thread(target=worker,daemon=True).start()
    bt=ttk.Button(painel,text='Gerar relatório HTML',command=iniciar);bt.grid(row=13,column=0,columnspan=3,sticky='e',pady=14)
    def acompanhar():
        nonlocal ocupado
        try:
            while True:
                kind,v=fila.get_nowait()
                if kind=='progresso':status.set(v);continue
                ocupado=False;barra.stop();cb.configure(state='readonly');bt.configure(state='normal')
                for w in widgets:w.configure(state='readonly' if w in [a[0] for a in arquivo_widgets.values()] else 'normal')
                alternar()
                if kind=='erro':status.set('Geração interrompida.');messagebox.showerror('Comparação interrompida',v,parent=raiz)
                else:
                    path,_=v
                    config.write_text(json.dumps({k:v.get() for k,v in vs.items()},ensure_ascii=False,indent=2),encoding='utf-8')
                    status.set(f'Concluído: {path.name}');webbrowser.open(path.as_uri())
        except queue.Empty:pass
        raiz.after(150,acompanhar)
    def fechar():
        if ocupado:messagebox.showinfo('Geração em andamento','Aguarde a conclusão.',parent=raiz)
        else:raiz.destroy()
    raiz.protocol('WM_DELETE_WINDOW',fechar);raiz.after(150,acompanhar);raiz.mainloop()


def main():
    parser = argparse.ArgumentParser(description="Compara os parâmetros dos dois modelos e gera um HTML independente.")
    parser.add_argument("--tipo-comparacao", choices=["novo_newave", "novo_novo"], default="novo_newave")
    parser.add_argument("--deck-referencia", help="Deck da fonte B quando ambos os Parquets são do novo modelo")
    parser.add_argument("--rotulo-novo", help="Nome/versão da fonte A")
    parser.add_argument("--rotulo-referencia", help="Nome/versão da fonte B (referência)")
    parser.add_argument("--novo", help="Parquet enriquecido do novo modelo")
    parser.add_argument("--newave", help="Parquet B: NEWAVE v2 ou novo modelo, conforme --tipo-comparacao")
    parser.add_argument("--deck", help="Pasta do deck do novo modelo")
    parser.add_argument("--deck-newave", help="Pasta NEWAVE opcional para conferir o dger.dat")
    parser.add_argument("--saida", help="Caminho do HTML; padrão: relatorios/comparacao_parametros_DATA_HORA.html")
    parser.add_argument("--sem-abrir", action="store_true", help="Não abrir o navegador após gerar")
    args = parser.parse_args()
    garantir_dependencias({"pyarrow": "pyarrow>=14", "duckdb": "duckdb>=1.0"})
    if not sys.argv[1:]:
        janela()
        return 0
    if not all((args.novo, args.newave, args.deck)):
        parser.error("Informe --novo, --newave e --deck, ou execute sem argumentos para abrir a janela.")
    try:
        caminho, _ = gerar(args.novo, args.newave, args.deck, args.saida, args.deck_newave,
                           tipo_comparacao=args.tipo_comparacao, deck_referencia=args.deck_referencia,
                           rotulo_novo=args.rotulo_novo, rotulo_referencia=args.rotulo_referencia)
    except Exception as erro:
        print(f"\nNão foi gerado um novo relatório:\n{erro}", file=sys.stderr)
        return 2
    if not args.sem_abrir:
        webbrowser.open(caminho.as_uri())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
