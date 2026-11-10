"""Validação entre anos e contagem mensal, sem alterar valores ou tolerâncias."""
from copy import deepcopy
from datetime import date
import json
import math
import unittest

from comparador.dados import ErroConsistencia, proximo_mes
from comparador.executar import gerar
from comparador.regras import comparar
from testes import test_comparador as fixtures


class ConsolidacaoMensalTest(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.ComparadorTest()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        f = self.f
        originais_a, originais_b = f.a, f.b
        f.a, f.b = [], []
        stages_a, stages_b = [], []
        for s in range(24):
            data = date(2026 + s // 12, s % 12 + 1, 1)
            intervalo = dict(start_date=str(data), end_date=str(proximo_mes(data)))
            stages_a.append(dict(id=17+s, **intervalo))
            stages_b.append(dict(stage_id=s, **intervalo))
            for h in range(2):
                # A variação entre meses é legítima; somente o mesmo mês se repete.
                origem = 1 if data.month == 9 else 0
                for c in range(3):
                    f.a.append(dict(originais_a[h*6+origem*3+c], stage_id=17+s))
                    f.b.append(dict(originais_b[h*6+origem*3+c], stage_id=s))
        f.salvar_json(f.deck/'stages.json', dict(stages=stages_a))
        f.meta[b'stage_mapping'] = json.dumps(stages_b).encode()
        f.gravar()

    def test_dois_anos_conservam_todas_as_grandezas_e_contam_uma_vez(self):
        a, b = self.f.fontes()
        r = comparar(a, b)
        aa, bb = deepcopy(a), deepcopy(b)
        for fonte in (aa, bb):
            fonte.parametros = {k:v for k,v in fonte.parametros.items() if fonte.datas[k[1]].year == 2026}
            fonte.datas = {k:v for k,v in fonte.datas.items() if v.year == 2026}
        unico = comparar(aa, bb)
        self.assertEqual(r['totais'], unico['totais'])
        self.assertEqual(r['linhas'], unico['linhas'])
        self.assertEqual(r['tolerancias'], unico['tolerancias'])
        self.assertEqual(r['meses'], list(range(1, 13)))
        self.assertEqual(len(r['datas']), 24)
        self.assertEqual(len(r['linhas']), 24)
        for p in r['linhas']:
            self.assertEqual(len(p[4]), len(r['campos']))
            self.assertEqual(p[4], [a.parametros[r['usinas'][p[0]][1], p[2]][c] for c in r['campos']])
        for fonte in r['fontes']:
            self.assertEqual(fonte['pares'], 48)
            self.assertEqual(fonte['validacao_mensal']['conjuntos'], 24)
            self.assertEqual(fonte['validacao_mensal']['grupos_sem_repeticao'], 0)

    def test_variacao_entre_anos_bloqueia_mesmo_quando_diferenca_seria_aprovada(self):
        originais = self.f.fontes()
        for numero in (0, 1):
            for campo in originais[numero].colunas:
                with self.subTest(fonte=numero, campo=campo):
                    fontes = deepcopy(originais)
                    fonte = fontes[numero]
                    hid = next(iter(fonte.nomes))
                    sid = next(s for s,d in fonte.datas.items() if d == date(2027, 1, 1))
                    valores = fonte.parametros[hid, sid]
                    if campo == 'ar_order':
                        valores[campo] = 0
                    elif valores[campo] is None:
                        valores[campo] = 0.
                    else:
                        valores[campo] = math.nextafter(valores[campo], math.inf)
                    with self.assertRaises(ErroConsistencia) as erro:
                        comparar(*fontes)
                    for trecho in ('variam entre anos', fonte.caminho, fonte.nomes[hid], campo, '01/2026', '01/2027'):
                        self.assertIn(trecho, str(erro.exception))

    def test_duas_grandezas_divergentes_no_mes_contam_duas_sem_repetir_anos(self):
        a, b = self.f.fontes()
        # Igualar fontes somente nesta amostra artificial e isolada do teste.
        for (hid, sid), valores in b.parametros.items():
            valores.update(a.parametros[hid-83, sid+17])
        for sid in (17, 29):
            a.parametros[7, sid]['annual_mean_m3s'] += 10
            a.parametros[7, sid]['seasonal_std_m3s'] += 10
        r = comparar(a, b)
        self.assertEqual(r['totais']['fora'], 2)
        self.assertEqual(r['totais']['sc'], 0)
        janeiro = next(p for p in r['linhas'] if p[0] == 0 and r['meses'][p[1]] == 1)
        self.assertEqual(janeiro[7].count(1), 2)

    def test_sc_zero_ativo_e_lags_inativos_preservados(self):
        a, b = self.f.fontes()
        for fonte in (a, b):
            for valores in fonte.parametros.values():
                valores.update(ar_order=1, ar_coefficient_lag_1=0., ar_coefficient_lag_2=None)
        for sid in (17, 29):
            a.parametros[7, sid].update(ar_order=2, ar_coefficient_lag_2=0.)
        r = comparar(a, b)
        self.assertEqual(r['totais']['sc'], 2)
        for p in r['linhas']:
            self.assertEqual(p[4][1], 0.)
            self.assertEqual(p[7][1], 0 if p[4][0]==p[5][0] else 2)
            if p[4][0]!=p[5][0]:
                self.assertEqual(p[8][1:3],[None,None])
        self.assertEqual(r['totais']['comparaveis'], 24*7-1)

    def test_mesmos_meses_com_horizonte_diferente_continuam_bloqueados(self):
        a, b = self.f.fontes()
        b.datas = {s:d.replace(year=d.year+1) for s,d in b.datas.items()}
        with self.assertRaisesRegex(ErroConsistencia, 'Comparação bloqueada'):
            comparar(a, b)

    def test_horizonte_parcial_nao_inventa_meses_e_ordena_por_mes_do_ano(self):
        a, b = self.f.fontes()
        for fonte in (a, b):
            fonte.datas = {s:d for s,d in fonte.datas.items() if date(2026,12,1) <= d <= date(2027,2,1)}
            fonte.parametros = {k:v for k,v in fonte.parametros.items() if k[1] in fonte.datas}
        r = comparar(a, b)
        self.assertEqual(r['meses'], [1, 2, 12])
        self.assertEqual(len(r['linhas']), 6)
        for fonte in r['fontes']:
            self.assertEqual(fonte['validacao_mensal']['grupos_sem_repeticao'], 6)
            self.assertEqual(fonte['validacao_mensal']['grupos_com_repeticao'], 0)

    def test_pipeline_bloqueia_variacao_anual_e_preserva_html_anterior(self):
        f = self.f
        destino = f.pasta/'mensal.html'
        gerar(f.novo, f.nw, f.deck, destino, progresso=lambda _:None)
        antes = destino.read_bytes()
        for linha in f.a:
            if linha['hydro_id'] == 7 and linha['stage_id'] == 29:
                linha['annual_coefficient'] = math.nextafter(linha['annual_coefficient'], math.inf)
        f.gravar()
        with self.assertRaisesRegex(ErroConsistencia, 'variam entre anos'):
            gerar(f.novo, f.nw, f.deck, destino, progresso=lambda _:None)
        self.assertEqual(destino.read_bytes(), antes)

    def test_pipeline_duas_versoes_consolida_e_identifica_fonte_b_inconsistente(self):
        f = self.f
        deck_b = f.pasta/'deck_b'
        (deck_b/'system').mkdir(parents=True)
        f.salvar_json(deck_b/'system/hydros.json', dict(hydros=[dict(id=90,name='CAMARGOS'),dict(id=91,name='FURNAS')]))
        stages = json.loads(f.meta[b'stage_mapping'])
        f.salvar_json(deck_b/'stages.json', dict(stages=[dict(id=s['stage_id'],start_date=s['start_date'],end_date=s['end_date']) for s in stages]))
        import pyarrow.parquet as pq
        tabela = pq.read_table(f.nw).replace_schema_metadata({b'source_model':b'COBRE'})
        arquivo_b = f.pasta/'cobre_b.parquet'
        pq.write_table(tabela, arquivo_b)
        args = dict(tipo_comparacao='novo_novo', deck_referencia=deck_b, progresso=lambda _:None)
        _, r = gerar(f.novo, arquivo_b, f.deck, f.pasta/'duas.html', **args)
        self.assertEqual(len(r['linhas']), 24)
        linhas = tabela.to_pylist()
        for linha in linhas:
            if linha['hydro_id'] == 90 and linha['stage_id'] == 12:
                linha['annual_std_m3s'] += 1
        import pyarrow as pa
        pq.write_table(pa.Table.from_pylist(linhas,schema=tabela.schema), arquivo_b)
        with self.assertRaises(ErroConsistencia) as erro:
            gerar(f.novo, arquivo_b, f.deck, f.pasta/'duas.html', **args)
        self.assertIn(str(arquivo_b.resolve()), str(erro.exception))
