"""Diferenças absolutas, precisão por tipo e resultados calculados antes do HTML."""

from datetime import datetime
from decimal import Decimal, InvalidOperation
import math

from .dados import ESTATISTICAS, parear


NOMES = {
    "ar_order": "Ordem PARP",
    "annual_coefficient": "Coeficiente anual",
    "annual_mean_m3s": "Média da componente anual",
    "annual_std_m3s": "Desvio padrão da componente anual",
    "seasonal_mean_m3s": "Média mensal",
    "seasonal_std_m3s": "Desvio padrão mensal",
}
MOMENTOS = {c for c in ESTATISTICAS if c.endswith("_m3s")}


def tipo(campo):
    return "ar_coefficient" if campo.startswith("ar_coefficient_lag_") else campo


def validar_percentual(valor):
    """Percentual informado antes da geração; aceita ponto ou vírgula decimal."""
    try:
        if isinstance(valor, bool) or valor is None:
            raise InvalidOperation()
        texto = str(valor).strip().removesuffix("%").strip().replace(",", ".")
        numero = Decimal(texto)
        if not numero.is_finite() or numero < 0 or not math.isfinite(float(numero)):
            raise InvalidOperation()
    except (InvalidOperation, ValueError, OverflowError) as erro:
        raise ValueError("Informe o percentual para médias e desvios padrão: um número finito maior ou igual a zero, como 5 ou 2,5.") from erro
    return numero


def tolerancia_estatistica(valor_newave, percentual):
    """Limite absoluto para esta usina/estágio: x/100 × |NEWAVE|; zero continua zero."""
    limite = abs(Decimal(str(valor_newave))) * validar_percentual(percentual) / 100
    if not limite.is_finite() or not math.isfinite(float(limite)):
        raise ValueError("O percentual produz uma tolerância fora do limite numérico. Informe um percentual menor.")
    return limite


def precisao_newave(campo, valor):
    """Unidade inteira do formato impresso, sem aplicar o fator de incerteza 1/2."""
    if campo == "ar_order":
        return Decimal(0)
    if campo in ("annual_coefficient", "ar_coefficient") or campo.startswith("ar_coefficient_lag_"):
        numero = Decimal(str(abs(valor)))
        expoente = numero.adjusted() - 2 if numero else -3
        return Decimal(10) ** expoente
    return Decimal("0.01")


def tolerancia_valor(campo, valor, modelo):
    if campo in MOMENTOS:
        raise ValueError("Médias e desvios exigem percentual e referência NEWAVE por usina/estágio.")
    if campo == "ar_order":
        return Decimal(0)
    precisao = (precisao_newave(campo, valor) if modelo == "NEWAVE"
                else Decimal(str(math.ulp(float(valor)))))
    return precisao


def descricao_precisao(t, percentual=None):
    if t == "ar_order":
        return "Comparação exata de inteiros"
    if t in ("ar_coefficient", "annual_coefficient"):
        return "Unidade inteira de precisão · NEWAVE: 3 algarismos significativos; novo modelo: float64 nativo"
    x = format(validar_percentual(percentual).normalize(), "f").replace(".", ",")
    return f"{x}% de |NEWAVE|, calculado para cada usina e estágio; NEWAVE zero implica tolerância zero"


def calcular_tolerancias(novo, newave, campos):
    # None indica que o limite é específico de cada linha, e não global por tipo.
    tolerancias = {tipo(c): None if c in MOMENTOS else Decimal(0) for c in campos}
    for fonte in (novo, newave):
        for valores in fonte.parametros.values():
            for c in fonte.colunas:
                valor = valores[c]
                if valor is None or c == "ar_order" or c in MOMENTOS:
                    continue
                # O perfil NEWAVE vem do formato do PARPVAZ usado pelo conversor v2.
                # O novo modelo guarda doubles nativos, sem arredondamento textual.
                limite = tolerancia_valor(c, valor, fonte.modelo)
                tolerancias[tipo(c)] = max(tolerancias[tipo(c)], limite)
    return tolerancias


def comparar_valores(a, b, tolerancia):
    # Decimal(str(...)) evita reprovar um limite inclusivo por ruído da subtração binária.
    diferenca = abs(Decimal(str(a)) - Decimal(str(b)))
    return float(diferenca), 0 if diferenca <= tolerancia else 1


def comparar(novo, newave, progresso=lambda _: None, *, percentual_estatisticas):
    percentual = validar_percentual(percentual_estatisticas)
    pares = parear(novo, newave)
    maior_lag = max(len(novo.colunas), len(newave.colunas)) - 1 - len(ESTATISTICAS)
    campos = ["ar_order"] + [f"ar_coefficient_lag_{i}" for i in range(1, maior_lag + 1)] + ESTATISTICAS
    tolerancias = calcular_tolerancias(novo, newave, campos)
    usinas = sorted({(novo.nomes[a[0]], a[0], b[0]) for a, b, _ in pares}, key=lambda u: u[0])
    indices = {h: i for i, (_, h, _) in enumerate(usinas)}
    datas = sorted({data.isoformat()[:7] for _, _, data in pares})
    indices_datas = {d: i for i, d in enumerate(datas)}
    linhas = []
    totais = dict(pares=len(pares), comparaveis=0, dentro=0, fora=0, sc=0)
    for (hid, sid, a), (_, sid_nw, b), data in pares:
        va, vb, diferencas, resultados, limites = [], [], [], [], []
        for c in campos:
            x, y = a.get(c), b.get(c)
            lag = int(c.rsplit("_", 1)[1]) if c.startswith("ar_coefficient_lag_") else None
            ativo_a = lag is None or lag <= a["ar_order"]
            ativo_b = lag is None or lag <= b["ar_order"]
            limite = tolerancia_estatistica(y, percentual) if c in MOMENTOS else tolerancias[tipo(c)]
            if ativo_a and ativo_b:
                dif, resultado = comparar_valores(x, y, limite)
                totais["comparaveis"] += 1
                totais["dentro" if resultado == 0 else "fora"] += 1
            else:
                dif, resultado = None, 2
                if ativo_a or ativo_b:
                    totais["sc"] += 1
            va.append(x)
            vb.append(y)
            diferencas.append(dif)
            resultados.append(resultado)
            limites.append(float(limite))
        linhas.append([indices[hid], indices_datas[data.isoformat()[:7]], sid, sid_nw,
                       va, vb, diferencas, resultados, limites])
    precisao = []
    for t, tolerancia in tolerancias.items():
        texto = descricao_precisao(t, percentual)
        x = format(percentual.normalize(), "f").replace(".", ",")
        precisao.append([NOMES.get(t, "Coeficientes mensais (todos os lags)"),
                         float(tolerancia) if tolerancia is not None else f"{x}% × |NEWAVE| por usina e estágio",
                         "m³/s" if t.endswith("m3s") else "Adimensional", texto])
    resultado = dict(
        versao=3, criterio_coeficientes="unidade_inteira_precisao",
        criterio_estatisticas="percentual_newave_por_usina_estagio",
        percentual_estatisticas=float(percentual), percentual_estatisticas_decimal=str(percentual),
        gerado_em=datetime.now().astimezone().isoformat(timespec="seconds"),
        campos=campos, nomes_campos=[NOMES.get(c, "Coeficiente mensal — lag " + c.rsplit("_", 1)[-1]) for c in campos],
        tolerancias=[float(tolerancias[tipo(c)]) if tolerancias[tipo(c)] is not None else None for c in campos],
        usinas=usinas, datas=datas, linhas=linhas, totais=totais, precisao=precisao,
        fontes=[dict(modelo=f.modelo, caminho=f.caminho, registros=f.registros,
                     pares=len(f.parametros), usinas=len(f.nomes), meses=len(f.datas)) for f in (novo, newave)],
    )
    progresso(f"Comparações concluídas: {totais['comparaveis']} comparáveis; {totais['fora']} fora da tolerância; {totais['sc']} sc.")
    return resultado
