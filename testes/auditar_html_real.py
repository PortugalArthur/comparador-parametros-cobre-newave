"""Confronta o último HTML com os parquets e refaz as contas independentemente."""
from collections import Counter
from decimal import Decimal
import json
import math
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from infraestrutura.preparar_ambiente import garantir_dependencias
garantir_dependencias({})
from comparador.dados import ler_fonte


def normalizar(nome):
    import unicodedata
    value = unicodedata.normalize('NFKD', nome.upper())
    return ''.join(c for c in value if c.isascii() and c.isalnum())


def auditar(caminho=None):
    path = Path(caminho) if caminho else max((ROOT / 'relatorios').glob('*.html'), key=lambda p: p.stat().st_mtime_ns)
    html = path.read_text(encoding='utf-8')
    match = re.search(r'<script id="dados" type="application/json">(.*?)</script>', html, re.S)
    d = json.loads(match.group(1))
    assert (ROOT / 'recursos/interacao.js').read_text(encoding='utf-8') in html
    assert d['versao'] == 6 and d['unidade_comparacao'] == 'usina_mes_do_ano'
    assert d['criterio_ordens_coeficientes'] == 'ordens_iguais_obrigatorias'
    assert d['criterio_estatisticas'] == 'absoluta_fixa_0_01_m3s'
    assert 'percentual_estatisticas' not in d
    duas_versoes = d.get('tipo_comparacao') == 'novo_novo'
    assert d['criterio_coeficientes'] == ('unidade_inteira_precisao' if duas_versoes else 'precisao_newave_por_coeficiente')
    sources = [ler_fonte(d['fontes'][0]['caminho'], 'Novo modelo', d['deck_novo_modelo']),
               ler_fonte(d['fontes'][1]['caminho'], 'Novo modelo' if duas_versoes else 'NEWAVE',
                         d.get('deck_referencia') if duas_versoes else None)]
    for actual, embedded in zip(sources, d['fontes']):
        assert actual.registros == embedded['registros']
        assert len(actual.parametros) == embedded['pares']
    # Indexação independente: o nome normalizado e a data são a chave,
    # enquanto os IDs de cada modelo permanecem separados.
    indexed = []
    for source in sources:
        rows = {}
        for (hid, sid), values in source.parametros.items():
            key = normalizar(source.nomes[hid]), source.datas[sid].isoformat()[:7]
            assert key not in rows
            rows[key] = (hid, sid, values)
        indexed.append(rows)
    assert indexed[0].keys() == indexed[1].keys()
    assert d['datas'] == sorted({data for _, data in indexed[0]})
    # Consolidação independente: conferir cada valor de todos os anos antes de
    # usar o valor comum. Nenhuma função de consolidação de produção é chamada.
    monthly = []
    for source, full, embedded in zip(sources, indexed, d['fontes']):
        groups, occurrences = {}, Counter()
        for (name, data), record in sorted(full.items()):
            key = name, int(data[5:7])
            occurrences[key] += 1
            if key in groups:
                assert groups[key][2] == record[2], (source.caminho, key, 'variação entre anos')
            else:
                groups[key] = record
        validation = embedded['validacao_mensal']
        assert validation['constantes_entre_anos'] is True
        assert validation['conjuntos'] == len(groups)
        assert validation['grupos_sem_repeticao'] == sum(n == 1 for n in occurrences.values())
        assert validation['grupos_com_repeticao'] == sum(n > 1 for n in occurrences.values())
        assert validation['anos_por_mes'] == {
            str(m): sorted({day.year for day in source.datas.values() if day.month == m})
            for m in sorted({day.month for day in source.datas.values()})}
        monthly.append(groups)
    indexed = monthly
    assert indexed[0].keys() == indexed[1].keys()
    assert d['meses'] == sorted({m for _, m in indexed[0]})
    coeff_tols = {'monthly': Decimal(0), 'annual': Decimal(0)}
    for source in sources if duas_versoes else []:
        for values in source.parametros.values():
            for field, value in values.items():
                if value is None or not (field.startswith('ar_coefficient_lag_') or field == 'annual_coefficient'):
                    continue
                kind = 'annual' if field == 'annual_coefficient' else 'monthly'
                if source.modelo == 'NEWAVE':
                    v = Decimal(str(abs(value)))
                    unit = Decimal(10) ** (v.adjusted() - 2) if v else Decimal('0.001')
                else:
                    unit = Decimal(str(math.ulp(value)))
                coeff_tols[kind] = max(coeff_tols[kind], unit)
    count = Counter()
    limites_coeficientes = {'monthly': set(), 'annual': set()}
    seen = set()
    for row in d['linhas']:
        plant = d['usinas'][row[0]]
        key = normalizar(plant[0]), d['meses'][row[1]]
        assert key not in seen
        seen.add(key)
        ha, sa, a = indexed[0][key]
        hb, sb, b = indexed[1][key]
        assert (ha, hb) == tuple(plant[1:])
        assert (sa, sb) == tuple(row[2:4])
        for i, field in enumerate(d['campos']):
            x, y = a.get(field), b.get(field)
            assert (x, y) == (row[4][i], row[5][i]), (key, field, 'valor de origem')
            lag = int(field.rsplit('_', 1)[1]) if field.startswith('ar_coefficient_lag_') else None
            active_a = lag is None or lag <= a['ar_order']
            active_b = lag is None or lag <= b['ar_order']
            comparar_lag = active_a and active_b and (lag is None or a['ar_order'] == b['ar_order'])
            if lag is not None and not comparar_lag:
                tol = None
            elif field == 'ar_order':
                tol = Decimal(0)
            elif field.endswith('_m3s'):
                tol = Decimal('0.01')
                assert d['tolerancias'][i] == .01
            elif not duas_versoes:
                # Expoente do formato 0.XXXE±YY, independentemente da rotina de produção.
                if y is None:
                    tol = None
                else:
                    referencia = Decimal(str(abs(y)))
                    expoente = referencia.adjusted() + 1 if referencia else 0
                    tol = Decimal('0.001') * Decimal(10) ** expoente
                assert d['tolerancias'][i] is None
            else:
                tol = coeff_tols['monthly' if lag else 'annual']
                assert d['tolerancias'][i] == float(tol)
            assert row[8][i] == (float(tol) if tol is not None else None), (key, field, 'tolerancia')
            if (lag or field == 'annual_coefficient') and tol is not None:
                limites_coeficientes['monthly' if lag else 'annual'].add(float(tol))
            if comparar_lag:
                delta = abs(Decimal(str(x)) - Decimal(str(y)))
                status = 0 if delta <= tol else 1
                assert row[6][i] == float(delta)
                count['comparaveis'] += 1
                count['dentro' if status == 0 else 'fora'] += 1
            else:
                status = 2
                assert row[6][i] is None
                if active_a or active_b:
                    count['sc'] += 1
                else:
                    count['inativos_nos_dois'] += 1
            assert row[7][i] == status, (key, field, 'classificacao')
    assert seen == indexed[0].keys()
    assert len(d['linhas']) == d['totais']['pares']
    for field in ['comparaveis', 'dentro', 'fora', 'sc']:
        assert count[field] == d['totais'][field], field
    return dict(html=str(path), pares=len(seen), usinas=len(d['usinas']), meses_do_ano=len(d['meses']), meses_no_horizonte=len(d['datas']),
                tolerancia_estatisticas_m3s=.01, contagens=dict(count),
                tolerancias_coeficientes={k: sorted(v) for k, v in limites_coeficientes.items()},
                divergencias=0, linhas_parquets_conferidas=sum(s.registros for s in sources))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    result = auditar(sys.argv[1] if len(sys.argv) > 1 else None)
    folder = ROOT / 'outputs/verificacao/consolidacao_mensal' / Path(result['html']).stem
    folder.mkdir(parents=True, exist_ok=True)
    (folder / 'resultado.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))
