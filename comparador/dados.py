"""Leitura de parâmetros e pareamento por usina e data, sem recalcular ajustes."""

from dataclasses import dataclass
from datetime import date
import json
import math
from pathlib import Path
import re
import unicodedata

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq


ESTATISTICAS = ["annual_coefficient", "annual_mean_m3s", "annual_std_m3s",
                "seasonal_mean_m3s", "seasonal_std_m3s"]


class ErroConsistencia(ValueError):
    """Uma comparação não pode continuar com entradas inconsistentes."""


def normalizar(texto):
    texto = unicodedata.normalize("NFKD", str(texto).upper())
    return re.sub(r"[^A-Z0-9]", "", "".join(c for c in texto if not unicodedata.combining(c)))


def proximo_mes(data):
    return date(data.year + (data.month == 12), data.month % 12 + 1, 1)


def inteiro(valor):
    return isinstance(valor, int) and not isinstance(valor, bool)


def carregar_json(caminho):
    try:
        return json.loads(Path(caminho).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as erro:
        raise ErroConsistencia(f"JSON inválido ou ilegível: {caminho}") from erro


def calendario(registros, origem, campo_id="stage_id"):
    if not isinstance(registros, list) or not registros:
        raise ErroConsistencia(f"{origem}: calendário ausente.")
    saida, datas = {}, set()
    for r in registros:
        try:
            sid = r[campo_id]
            inicio = date.fromisoformat(r["start_date"])
            fim = date.fromisoformat(r["end_date"])
            if (not inteiro(sid) or sid in saida or inicio in datas or inicio.day != 1
                    or fim != proximo_mes(inicio)):
                raise ValueError()
        except (ValueError, TypeError, KeyError) as erro:
            raise ErroConsistencia(f"{origem}: estágio duplicado ou intervalo mensal inválido: {r!r}") from erro
        saida[sid] = inicio
        datas.add(inicio)
    return saida


def cadastro(registros, origem, campo_id, campo_nome):
    saida, nomes = {}, set()
    if not isinstance(registros, list) or not registros:
        raise ErroConsistencia(f"{origem}: cadastro de usinas ausente.")
    for r in registros:
        if not isinstance(r, dict):
            raise ErroConsistencia(f"{origem}: registro de usina inválido.")
        hid, nome = r.get(campo_id), r.get(campo_nome)
        chave = normalizar(nome) if isinstance(nome, str) else ""
        if not inteiro(hid) or hid in saida or not chave or chave in nomes:
            raise ErroConsistencia(f"{origem}: ID ou nome de usina ausente, duplicado ou ambíguo: {r!r}")
        saida[hid] = nome.strip()
        nomes.add(chave)
    return saida


def ler_deck(pasta):
    pasta = Path(pasta)
    hydros = carregar_json(pasta / "system/hydros.json")
    stages = carregar_json(pasta / "stages.json")
    if not isinstance(hydros, dict) or not isinstance(stages, dict):
        raise ErroConsistencia("O deck deve conter objetos JSON de cadastro e calendário.")
    return (cadastro(hydros.get("hydros"), "Deck do novo modelo", "id", "name"),
            calendario(stages.get("stages"), "Deck do novo modelo", "id"))


@dataclass
class Fonte:
    modelo: str
    caminho: str
    colunas: list
    parametros: dict
    nomes: dict
    datas: dict
    registros: int
    metadata: dict


def ler_fonte(caminho, modelo, deck=None, progresso=lambda _: None):
    """Varre todas as linhas, validando constância antes de remover as repetições."""
    caminho = str(Path(caminho).resolve())
    progresso(f"Conferindo parâmetros de todas as linhas: {modelo}...")
    try:
        schema = pq.read_schema(caminho)
        metadata = {k.decode("utf-8"): v.decode("utf-8") for k, v in (schema.metadata or {}).items()}
    except Exception as erro:
        raise ErroConsistencia(f"Não foi possível ler o parquet {modelo}: {caminho}\n{erro}") from erro
    lags = sorted((c for c in schema.names if re.fullmatch(r"ar_coefficient_lag_[1-9]\d*", c)),
                  key=lambda c: int(c.rsplit("_", 1)[1]))
    if lags != [f"ar_coefficient_lag_{i}" for i in range(1, len(lags) + 1)]:
        raise ErroConsistencia(f"{modelo}: colunas de lags descontínuas.")
    campos = ["ar_order"] + lags + ESTATISTICAS
    faltantes = set(["hydro_id", "stage_id"] + campos) - set(schema.names)
    if faltantes:
        raise ErroConsistencia(f"{modelo}: parquet sem os parâmetros enriquecidos: {sorted(faltantes)}")
    for c in ["hydro_id", "stage_id", "ar_order"]:
        if not pa.types.is_integer(schema.field(c).type):
            raise ErroConsistencia(f"{modelo}: {c} deve ser inteiro.")
    for c in lags + ESTATISTICAS:
        if schema.field(c).type != pa.float64():
            raise ErroConsistencia(f"{modelo}: {c} deve ser float64, como no esquema dos geradores.")
    if modelo == "NEWAVE":
        if (metadata.get("source_model") != "NEWAVE" or metadata.get("newave_schema_version") != "2"
                or metadata.get("coefficient_basis") != "seasonal_standardized"
                or metadata.get("ar_max_order") != str(len(lags))):
            raise ErroConsistencia("NEWAVE: esquema/precisão não reconhecidos. Use o parquet enriquecido versão 2.")
        try:
            nomes = cadastro(json.loads(metadata["hydro_mapping"]), "NEWAVE", "hydro_id", "nome_usina_cadastro")
            datas = calendario(json.loads(metadata["stage_mapping"]), "NEWAVE")
        except (KeyError, ValueError) as erro:
            raise ErroConsistencia(f"NEWAVE: correspondências de usinas/datas inválidas: {erro}") from erro
    else:
        if metadata.get("source_model", "COBRE").upper() not in ("COBRE", "NOVOMODELO", "NOVO MODELO"):
            raise ErroConsistencia("A primeira entrada não é um parquet do novo modelo.")
        if deck is None:
            raise ErroConsistencia("Informe a pasta do deck do novo modelo para identificar usinas e datas.")
        nomes, datas = ler_deck(deck)

    # MIN/MAX e contagem não nula detectam parâmetros distintos ou parcialmente nulos.
    # Nomes SQL são somente os campos fixos e os lags validados por expressão regular.
    agregacoes = ", ".join(f'MIN("{c}"), MAX("{c}"), COUNT("{c}")' for c in campos)
    with duckdb.connect() as conexao:
        conexao.execute("SET threads=4")
        registros = conexao.execute(
            f"SELECT hydro_id, stage_id, COUNT(*), {agregacoes} FROM read_parquet(?) "
            "GROUP BY hydro_id, stage_id ORDER BY hydro_id, stage_id", [caminho]).fetchall()
    if not registros:
        raise ErroConsistencia(f"{modelo}: parquet vazio.")
    parametros, problemas = {}, []
    quantidade = 0
    for hid, sid, n, *resumos in registros:
        quantidade += n
        if hid not in nomes or sid not in datas:
            problemas.append(f"Usina/estágio ({hid}, {sid}) ausente no cadastro ou calendário.")
            continue
        valores = {}
        for i, c in enumerate(campos):
            minimo, maximo, contagem = resumos[3 * i:3 * i + 3]
            if contagem not in (0, n) or (contagem and
                    (minimo != maximo or not math.isfinite(minimo) or not math.isfinite(maximo))):
                problemas.append(f"UHE {hid}, estágio {sid}: {c} varia entre cenários, contém nulos parciais ou não é finito.")
            valores[c] = minimo
        ordem = valores["ar_order"]
        if not inteiro(ordem) or not 0 <= ordem <= len(lags):
            problemas.append(f"UHE {hid}, estágio {sid}: ordem inválida {ordem}.")
            continue
        for i, c in enumerate(lags, 1):
            if (i <= ordem) != (valores[c] is not None):
                problemas.append(f"UHE {hid}, estágio {sid}: {c} ativo ausente ou inativo não nulo.")
        for c in ESTATISTICAS:
            if valores[c] is None or ("std" in c and valores[c] < 0):
                problemas.append(f"UHE {hid}, estágio {sid}: {c} ausente ou desvio negativo.")
        parametros[hid, sid] = valores
    if problemas:
        raise ErroConsistencia(f"{modelo}: {len(problemas)} erro(s) de consistência. Exemplos:\n" + "\n".join(problemas[:20]))
    usados_h = {h for h, _ in parametros}
    usados_s = {s for _, s in parametros}
    grade = {(h, s) for h in usados_h for s in usados_s}
    if set(parametros) != grade:
        ausentes = sorted(grade - set(parametros))
        raise ErroConsistencia(f"{modelo}: grade incompleta de usinas e estágios; {len(ausentes)} par(es) ausente(s): {ausentes[:12]}")
    datas_usadas = sorted(datas[s] for s in usados_s)
    if any(b != proximo_mes(a) for a, b in zip(datas_usadas, datas_usadas[1:])):
        raise ErroConsistencia(f"{modelo}: lacuna no calendário mensal observado.")
    progresso(f"{modelo}: {quantidade} registros conferidos; {len(parametros)} pares usina–mês.")
    return Fonte(modelo, caminho, campos, parametros,
                 {h: nomes[h] for h in usados_h}, {s: datas[s] for s in usados_s}, quantidade, metadata)


def conferir_deck_newave(pasta, fonte):
    """Conferência opcional: calendário incorporado deve caber no horizonte do DGER."""
    caminho = next((p for p in Path(pasta).iterdir() if p.name.lower() == "dger.dat"), None)
    if caminho is None:
        raise ErroConsistencia("Deck NEWAVE sem dger.dat.")
    texto = caminho.read_text(encoding="latin1")
    valores = []
    for rotulo in ["MES INICIO DO ESTUDO", "ANO INICIO DO ESTUDO", "No. DE ANOS DO EST", "No. DE ANOS POS FINAL"]:
        match = re.search(r"^\s*" + re.escape(rotulo) + r"\s+(\d+)\b", texto, re.M | re.I)
        if not match:
            raise ErroConsistencia(f"dger.dat sem {rotulo}.")
        valores.append(int(match[1]))
    mes, ano, estudo, pos = valores
    try:
        inicio, fim = date(ano, mes, 1), date(ano + estudo + pos - 1, 12, 1)
    except ValueError as erro:
        raise ErroConsistencia("Horizonte inválido em dger.dat.") from erro
    if estudo < 1 or min(fonte.datas.values()) < inicio or max(fonte.datas.values()) > fim:
        raise ErroConsistencia("Datas do parquet NEWAVE incompatíveis com o horizonte de dger.dat.")


def consolidar_meses(fonte):
    """Conserva o valor original somente após conferir todos os anos, sem tolerância."""
    mensais, ocorrencias, problemas = {}, {}, []
    for (hid, sid), valores in sorted(fonte.parametros.items(), key=lambda r: fonte.datas[r[0][1]]):
        data = fonte.datas[sid]
        chave = hid, data.month
        ocorrencias[chave] = ocorrencias.get(chave, 0) + 1
        if chave not in mensais:
            mensais[chave] = (hid, sid, valores)
            continue
        _, anterior, base = mensais[chave]
        for campo in fonte.colunas:
            if valores[campo] != base[campo]:
                problemas.append(
                    f"Usina {fonte.nomes[hid]} (ID {hid}), mês {data.month:02d}, {campo}: "
                    f"{fonte.datas[anterior]:%m/%Y} = {base[campo]!r}; {data:%m/%Y} = {valores[campo]!r}.")
    if problemas:
        raise ErroConsistencia(
            f"{fonte.modelo} — {fonte.caminho}: parâmetros variam entre anos "
            f"({len(problemas)} divergência(s)). Consolidação mensal bloqueada. Exemplos:\n"
            + "\n".join(problemas[:20]))
    validacao = dict(constantes_entre_anos=True, conjuntos=len(mensais),
                     grupos_com_repeticao=sum(n > 1 for n in ocorrencias.values()),
                     grupos_sem_repeticao=sum(n == 1 for n in ocorrencias.values()),
                     anos_por_mes={str(m): sorted({d.year for d in fonte.datas.values() if d.month == m})
                                   for m in sorted({d.month for d in fonte.datas.values()})})
    return mensais, validacao


def parear(novo, newave):
    def indexar(fonte):
        return {(normalizar(fonte.nomes[h]), fonte.datas[s]): (h, s, valores)
                for (h, s), valores in fonte.parametros.items()}
    a, b = indexar(novo), indexar(newave)
    if a.keys() != b.keys():
        faltam_nw = sorted(a.keys() - b.keys())
        faltam_novo = sorted(b.keys() - a.keys())
        exemplos = [f"{u} — {d:%m/%Y}" for u, d in (faltam_nw + faltam_novo)[:15]]
        raise ErroConsistencia(
            f"Comparação bloqueada: {len(faltam_nw)} par(es) ausente(s) no NEWAVE e "
            f"{len(faltam_novo)} no novo modelo. Usina e mês/ano devem corresponder.\n" + "\n".join(exemplos))
    return [(a[k], b[k], k[1]) for k in sorted(a)]
