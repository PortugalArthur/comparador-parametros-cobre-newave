"""Diferenças absolutas, precisão por tipo e resultados calculados antes do HTML."""

from datetime import datetime
from decimal import Decimal
import math

from .dados import ESTATISTICAS, consolidar_meses, parear


NOMES = {
    "ar_order": "Ordem PARP",
    "annual_coefficient": "Coeficiente anual",
    "annual_mean_m3s": "Média da componente anual",
    "annual_std_m3s": "Desvio padrão da componente anual",
    "seasonal_mean_m3s": "Média mensal",
    "seasonal_std_m3s": "Desvio padrão mensal",
}
MOMENTOS = {c for c in ESTATISTICAS if c.endswith("_m3s")}
TOLERANCIA_MOMENTOS = Decimal("0.01")


def tipo(campo):
    return "ar_coefficient" if campo.startswith("ar_coefficient_lag_") else campo


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
        return TOLERANCIA_MOMENTOS
    if campo == "ar_order":
        return Decimal(0)
    precisao = (precisao_newave(campo, valor) if modelo == "NEWAVE"
                else Decimal(str(math.ulp(float(valor)))))
    return precisao


def descricao_precisao(t, *, coeficientes_por_valor=False):
    if t == "ar_order":
        return "Comparação exata de inteiros"
    if t in ("ar_coefficient", "annual_coefficient"):
        if coeficientes_por_valor:
            return "0,001 × 10^e do formato NEWAVE 0.XXXE±YY, por usina, mês e coeficiente; zero ativo usa e=0"
        return "Unidade inteira de precisão · NEWAVE: 3 algarismos significativos; novo modelo: float64 nativo"
    return "Tolerância absoluta fixa de 0,01 m³/s, inclusive para referência zero; unidade inteira da resolução de impressão NEWAVE"


def calcular_tolerancias(novo, newave, campos):
    coeficientes_por_valor = any(f.modelo == "NEWAVE" for f in (novo, newave))
    # None indica limite individual, armazenado no vetor de tolerâncias de cada linha.
    tolerancias = {tipo(c): None if coeficientes_por_valor and tipo(c) in ("ar_coefficient", "annual_coefficient")
                  else TOLERANCIA_MOMENTOS if c in MOMENTOS else Decimal(0) for c in campos}
    for fonte in (novo, newave):
        for valores in fonte.parametros.values():
            for c in fonte.colunas:
                valor = valores[c]
                if valor is None or c == "ar_order" or c in MOMENTOS or tolerancias[tipo(c)] is None:
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


def comparar(novo, newave, progresso=lambda _: None):
    pares_originais = parear(novo, newave)
    progresso("Conferindo igualdade exata dos parâmetros entre todos os anos de cada mês...")
    mensais_a, validacao_a = consolidar_meses(novo)
    mensais_b, validacao_b = consolidar_meses(newave)
    # Parear o horizonte completo antes de remover repetições entre anos.
    chaves = {(a[0], b[0], data.month) for a, b, data in pares_originais}
    pares = [(mensais_a[ha, mes], mensais_b[hb, mes], mes)
             for ha, hb, mes in sorted(chaves, key=lambda k: (novo.nomes[k[0]], k[2]))]
    maior_lag = max(len(novo.colunas), len(newave.colunas)) - 1 - len(ESTATISTICAS)
    campos = ["ar_order"] + [f"ar_coefficient_lag_{i}" for i in range(1, maior_lag + 1)] + ESTATISTICAS
    tolerancias = calcular_tolerancias(novo, newave, campos)
    coeficientes_por_valor = tolerancias["annual_coefficient"] is None
    usinas = sorted({(novo.nomes[a[0]], a[0], b[0]) for a, b, _ in pares}, key=lambda u: u[0])
    indices = {h: i for i, (_, h, _) in enumerate(usinas)}
    datas = sorted({data.isoformat()[:7] for _, _, data in pares_originais})
    meses = sorted({mes for _, _, mes in pares})
    indices_meses = {m: i for i, m in enumerate(meses)}
    linhas = []
    totais = dict(pares=len(pares), comparaveis=0, dentro=0, fora=0, sc=0)
    for (hid, sid, a), (_, sid_nw, b), mes in pares:
        ordens_iguais = a["ar_order"] == b["ar_order"]
        va, vb, diferencas, resultados, limites = [], [], [], [], []
        for c in campos:
            x, y = a.get(c), b.get(c)
            lag = int(c.rsplit("_", 1)[1]) if c.startswith("ar_coefficient_lag_") else None
            ativo_a = lag is None or lag <= a["ar_order"]
            ativo_b = lag is None or lag <= b["ar_order"]
            limite = None
            if ativo_a and ativo_b and (lag is None or ordens_iguais):
                limite = tolerancias[tipo(c)]
                if limite is None:
                    referencia = y if newave.modelo == "NEWAVE" else x
                    limite = tolerancia_valor(c, referencia, "NEWAVE")
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
            limites.append(float(limite) if limite is not None else None)
        linhas.append([indices[hid], indices_meses[mes], sid, sid_nw,
                       va, vb, diferencas, resultados, limites])
    precisao = []
    for t, tolerancia in tolerancias.items():
        texto = descricao_precisao(t, coeficientes_por_valor=coeficientes_por_valor)
        precisao.append([NOMES.get(t, "Coeficientes mensais (todos os lags)"),
                         float(tolerancia) if tolerancia is not None else "0,001 × 10^e do NEWAVE por coeficiente",
                         "m³/s" if t.endswith("m3s") else "Adimensional", texto])
    resultado = dict(
        versao=6, unidade_comparacao="usina_mes_do_ano",
        criterio_ordens_coeficientes="ordens_iguais_obrigatorias",
        criterio_coeficientes="precisao_newave_por_coeficiente" if coeficientes_por_valor else "unidade_inteira_precisao",
        criterio_estatisticas="absoluta_fixa_0_01_m3s", tolerancia_estatisticas_m3s=float(TOLERANCIA_MOMENTOS),
        gerado_em=datetime.now().astimezone().isoformat(timespec="seconds"),
        campos=campos, nomes_campos=[NOMES.get(c, "Coeficiente mensal — lag " + c.rsplit("_", 1)[-1]) for c in campos],
        tolerancias=[float(tolerancias[tipo(c)]) if tolerancias[tipo(c)] is not None else None for c in campos],
        usinas=usinas, datas=datas, meses=meses, linhas=linhas, totais=totais, precisao=precisao,
        fontes=[dict(modelo=f.modelo, caminho=f.caminho, registros=f.registros,
                     pares=len(f.parametros), usinas=len(f.nomes), meses=len(f.datas), validacao_mensal=v)
                for f, v in ((novo, validacao_a), (newave, validacao_b))],
    )
    progresso(f"Comparações concluídas: {totais['comparaveis']} comparáveis; {totais['fora']} fora da tolerância; {totais['sc']} sc.")
    return resultado
