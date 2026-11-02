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


def gerar(novo, newave, deck, saida=None, deck_newave=None, progresso=print, *, percentual_estatisticas=None):
    from .dados import conferir_deck_newave, ErroConsistencia, ler_fonte
    from .regras import comparar, validar_percentual
    from .relatorio import salvar_html

    percentual = validar_percentual(percentual_estatisticas)
    novo, newave, deck = (Path(p).resolve() for p in (novo, newave, deck))
    if novo == newave:
        raise ErroConsistencia("Selecione dois parquets distintos, um de cada modelo.")
    fontes = [novo, newave, deck / "system/hydros.json", deck / "stages.json"]
    if deck_newave:
        fontes.append(Path(deck_newave) / "dger.dat")
    try:
        antes = {p: (p.stat().st_size, p.stat().st_mtime_ns) for p in fontes}
    except OSError as erro:
        raise ErroConsistencia(f"Entrada não encontrada ou inacessível: {erro}") from erro
    if saida is None:
        saida = RAIZ / "relatorios" / ("comparacao_parametros_" + datetime.now().strftime("%Y%m%d_%H%M%S_%f") + ".html")
    saida = Path(saida).resolve()
    if saida.suffix.lower() != ".html" or saida in fontes:
        raise ErroConsistencia("Escolha um arquivo de saída .html diferente das fontes.")
    a = ler_fonte(novo, "Novo modelo", deck, progresso)
    b = ler_fonte(newave, "NEWAVE", progresso=progresso)
    if deck_newave:
        conferir_deck_newave(deck_newave, b)
    resultado = comparar(a, b, progresso, percentual_estatisticas=percentual)
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

    raiz = tk.Tk()
    raiz.title("Comparador de parâmetros — novo modelo × NEWAVE")
    raiz.geometry("850x690")
    raiz.minsize(720, 650)
    raiz.configure(background="#f3f6fa")
    estilo = ttk.Style(raiz)
    estilo.theme_use("clam")
    estilo.configure("TFrame", background="#f3f6fa")
    estilo.configure("TLabel", background="#f3f6fa", foreground="#102a43", font=("Segoe UI", 10))
    estilo.configure("Titulo.TLabel", font=("Segoe UI", 19, "bold"), foreground="#154765")
    estilo.configure("TButton", font=("Segoe UI", 10), padding=8)
    estilo.configure("Gerar.TButton", background="#154765", foreground="white")
    estilo.map("Gerar.TButton", background=[("active", "#10364d")])
    painel = ttk.Frame(raiz, padding=26)
    painel.pack(fill="both", expand=True)
    painel.columnconfigure(0, weight=1)
    ttk.Label(painel, text="Novo modelo × NEWAVE", style="Titulo.TLabel").grid(row=0, column=0, columnspan=2, sticky="w")
    ttk.Label(painel, text="Compare os parâmetros de todas as usinas e gere um relatório HTML com tabelas.").grid(
        row=1, column=0, columnspan=2, sticky="w", pady=(7, 20))
    desktop = RAIZ.parent
    padroes = {
        "novo": str(desktop / "TESTES_ESTATISTICOS_COBRE/parquet gerado novo modelo/inflows_with_lags.parquet"),
        "newave": str(desktop / "TESTES_ESTATISTICOS_COBRE/parquet gerado newave/inflows_newave.parquet"),
        "deck": str(desktop / "Series_sinsteticas/DECK_COBRE"),
        "percentual_estatisticas": "",
    }
    config = RAIZ / ".ultimas_entradas.json"
    try:
        anterior = json.loads(config.read_text(encoding="utf-8"))
        if isinstance(anterior, dict):
            padroes.update({k: v for k, v in anterior.items() if k in padroes and isinstance(v, str)})
    except (OSError, ValueError):
        pass
    variaveis, botoes = {}, []
    for i, (chave, titulo) in enumerate([("novo", "1. Parquet do novo modelo (COBRE)"),
                                        ("newave", "2. Parquet enriquecido do NEWAVE"),
                                        ("deck", "3. Pasta do deck do novo modelo")]):
        linha = 2 + i * 2
        ttk.Label(painel, text=titulo).grid(row=linha, column=0, columnspan=2, sticky="w", pady=(8, 4))
        v = tk.StringVar(value=padroes[chave] if Path(padroes[chave]).exists() else "")
        variaveis[chave] = v
        entrada = ttk.Entry(painel, textvariable=v, state="readonly")
        entrada.grid(row=linha+1, column=0, sticky="ew", padx=(0, 10))
        def escolher(c=chave, t=titulo, var=v):
            inicial = Path(var.get()).parent if var.get() else desktop
            valor = (filedialog.askdirectory(title=t+" — contém system/hydros.json e stages.json", parent=raiz,
                                             initialdir=inicial) if c == "deck" else
                     filedialog.askopenfilename(title=t, filetypes=[("Parquet", "*.parquet")], parent=raiz,
                                                initialdir=inicial))
            if valor:
                var.set(valor)
        b = ttk.Button(painel, text="Selecionar…", command=escolher)
        b.grid(row=linha+1, column=1, sticky="e")
        botoes.append(b)
    ttk.Label(painel, text="4. Tolerância para médias e desvios padrão (% do valor NEWAVE)").grid(
        row=8, column=0, columnspan=2, sticky="w", pady=(20, 4))
    percentual = tk.StringVar(value=padroes["percentual_estatisticas"])
    variaveis["percentual_estatisticas"] = percentual
    entrada_percentual = ttk.Entry(painel, textvariable=percentual, width=14)
    entrada_percentual.grid(row=9, column=0, sticky="w")
    botoes.append(entrada_percentual)
    ttk.Label(painel, text="Informe x antes de gerar. Exemplo: 5 significa 5%; também aceita 2,5.\n"
              "Tolerância = x/100 × |NEWAVE| para cada usina e estágio; NEWAVE zero → tolerância zero.").grid(
                  row=10, column=0, columnspan=2, sticky="w", pady=(5, 12))
    ttk.Label(painel, text="O cadastro e as datas do NEWAVE serão lidos do próprio parquet.\n"
              "Saída: pasta relatorios deste programa. As fontes serão apenas lidas.").grid(
                  row=11, column=0, columnspan=2, sticky="w", pady=(4, 14))
    status = tk.StringVar(value="Confira as entradas e clique em Gerar relatório HTML.")
    ttk.Label(painel, textvariable=status, wraplength=760).grid(row=12, column=0, columnspan=2, sticky="w", pady=(0, 10))
    barra = ttk.Progressbar(painel, mode="indeterminate")
    barra.grid(row=13, column=0, columnspan=2, sticky="ew", pady=(0, 14))
    eventos = queue.Queue()
    ocupado = False

    def acompanhar():
        nonlocal ocupado
        try:
            while True:
                tipo, valor = eventos.get_nowait()
                if tipo == "progresso":
                    status.set(valor)
                else:
                    ocupado = False
                    barra.stop()
                    for b in botoes:
                        b.configure(state="normal")
                    if tipo == "erro":
                        status.set("Não foi gerado um novo relatório. Confira a mensagem de consistência.")
                        messagebox.showerror("Comparação interrompida", valor, parent=raiz)
                    else:
                        caminho, resultado = valor
                        status.set(f"Concluído: {len(resultado['usinas'])} usinas, {len(resultado['datas'])} meses. HTML salvo em relatorios.")
                        try:
                            config.write_text(json.dumps({k: v.get() for k, v in variaveis.items()}, ensure_ascii=False, indent=2), encoding="utf-8")
                        except OSError:
                            pass
                        webbrowser.open(caminho.as_uri())
                        messagebox.showinfo("Relatório gerado", f"O HTML foi salvo e aberto no navegador:\n\n{caminho}", parent=raiz)
        except queue.Empty:
            pass
        raiz.after(120, acompanhar)

    def iniciar():
        nonlocal ocupado
        entradas = {k: v.get() for k, v in variaveis.items()}
        if not all(entradas[k] for k in ("novo", "newave", "deck")):
            messagebox.showerror("Entradas incompletas", "Selecione os dois parquets e a pasta do deck do novo modelo.", parent=raiz)
            return
        from .regras import validar_percentual
        try:
            entradas["percentual_estatisticas"] = validar_percentual(entradas["percentual_estatisticas"])
        except ValueError as erro:
            messagebox.showerror("Percentual obrigatório", str(erro), parent=raiz)
            entrada_percentual.focus_set()
            return
        ocupado = True
        for b in botoes:
            b.configure(state="disabled")
        barra.start(12)
        def trabalhar():
            try:
                valor = gerar(**entradas, progresso=lambda t: eventos.put(("progresso", t)))
                eventos.put(("concluido", valor))
            except Exception as erro:
                eventos.put(("erro", str(erro)))
        threading.Thread(target=trabalhar, daemon=True).start()

    gerar_botao = ttk.Button(painel, text="Gerar relatório HTML", command=iniciar, style="Gerar.TButton")
    gerar_botao.grid(row=14, column=0, columnspan=2, sticky="e")
    botoes.append(gerar_botao)
    def fechar():
        if ocupado:
            messagebox.showinfo("Comparação em andamento", "Aguarde a conclusão para fechar esta janela.", parent=raiz)
        else:
            raiz.destroy()
    raiz.protocol("WM_DELETE_WINDOW", fechar)
    raiz.after(120, acompanhar)
    raiz.mainloop()


def main():
    parser = argparse.ArgumentParser(description="Compara os parâmetros dos dois modelos e gera um HTML independente.")
    parser.add_argument("--novo", help="Parquet enriquecido do novo modelo")
    parser.add_argument("--newave", help="Parquet NEWAVE enriquecido versão 2")
    parser.add_argument("--deck", help="Pasta do deck do novo modelo")
    parser.add_argument("--deck-newave", help="Pasta NEWAVE opcional para conferir o dger.dat")
    parser.add_argument("--saida", help="Caminho do HTML; padrão: relatorios/comparacao_parametros_DATA_HORA.html")
    parser.add_argument("--percentual-estatisticas", help="Obrigatório na linha de comando: x%% de |NEWAVE| para médias e desvios; aceita vírgula decimal")
    parser.add_argument("--sem-abrir", action="store_true", help="Não abrir o navegador após gerar")
    args = parser.parse_args()
    garantir_dependencias({"pyarrow": "pyarrow>=14", "duckdb": "duckdb>=1.0"})
    if not sys.argv[1:]:
        janela()
        return 0
    if not all((args.novo, args.newave, args.deck)):
        parser.error("Informe --novo, --newave e --deck, ou execute sem argumentos para abrir a janela.")
    if args.percentual_estatisticas is None:
        parser.error("Informe --percentual-estatisticas com o percentual escolhido para médias e desvios padrão.")
    try:
        caminho, _ = gerar(args.novo, args.newave, args.deck, args.saida, args.deck_newave,
                           percentual_estatisticas=args.percentual_estatisticas)
    except Exception as erro:
        print(f"\nNão foi gerado um novo relatório:\n{erro}", file=sys.stderr)
        return 2
    if not args.sem_abrir:
        webbrowser.open(caminho.as_uri())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
