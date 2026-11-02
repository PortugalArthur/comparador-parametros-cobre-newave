"""Monta um único HTML autossuficiente, sem executar código do HTML de referência."""

import json
import os
from pathlib import Path
import tempfile


RAIZ = Path(__file__).resolve().parents[1]


def salvar_html(resultado, destino):
    destino = Path(destino).resolve()
    destino.parent.mkdir(parents=True, exist_ok=True)
    recursos = RAIZ / "recursos"
    dados = json.dumps(resultado, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
    # Não permitir que nomes/caminhos encerrem a tag de dados ou introduzam HTML.
    dados = (dados.replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")
             .replace("\u2028", "\\u2028").replace("\u2029", "\\u2029"))
    pagina = (recursos / "relatorio.html").read_text(encoding="utf-8")
    pagina = pagina.replace("/*__ESTILOS__*/", (recursos / "estilos.css").read_text(encoding="utf-8"))
    pagina = pagina.replace("/*__INTERACAO__*/", (recursos / "interacao.js").read_text(encoding="utf-8"))
    pagina = pagina.replace("__DADOS_JSON__", dados)
    temporario = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n",
                                         dir=destino.parent, suffix=".tmp", delete=False) as arquivo:
            temporario = Path(arquivo.name)
            arquivo.write(pagina)
        os.replace(temporario, destino)
    finally:
        if temporario is not None and temporario.exists():
            temporario.unlink()
    return destino
