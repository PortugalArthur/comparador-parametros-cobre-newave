"""Duas fontes COBRE: mesmos cálculos, pareamento próprio e nomes de versão."""
import json
import math
from pathlib import Path
import unittest

import pyarrow as pa
import pyarrow.parquet as pq

from comparador.executar import gerar
from comparador.dados import ErroConsistencia, ler_fonte
from comparador.regras import comparar
from testes import test_comparador as fixtures


class DuasVersoesTest(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.ComparadorTest();self.f.setUp();self.addCleanup(self.f.doCleanups)
        f=self.f
        self.deck_b=f.pasta/'deck_b';(self.deck_b/'system').mkdir(parents=True)
        f.salvar_json(self.deck_b/'system/hydros.json',{'hydros':[{'id':107,'name':'CAMARGOS'},{'id':108,'name':'FURNAS'}]})
        d=json.loads((f.deck/'stages.json').read_text())
        for e in d['stages']:e['id']+=200
        f.salvar_json(self.deck_b/'stages.json',d)
        self.b=[dict(r,hydro_id=r['hydro_id']+100,stage_id=r['stage_id']+200) for r in f.a]
        self.parquet_b=f.pasta/'versao_b.parquet';self.gravar_b()

    def gravar_b(self):
        schema=pq.read_schema(self.f.novo).remove_metadata().with_metadata({b'source_model':b'COBRE'})
        pq.write_table(pa.Table.from_pylist(self.b,schema=schema),self.parquet_b)

    def gerar(self,**kw):
        return gerar(self.f.novo,self.parquet_b,self.f.deck,self.f.pasta/'versoes.html',
                     tipo_comparacao='novo_novo',deck_referencia=self.deck_b,progresso=lambda _:None,**kw)

    def test_arquivos_numericamente_iguais_tem_diferencas_zero_com_ids_distintos(self):
        path,r=self.gerar(rotulo_novo='COBRE 0.19.1',rotulo_referencia='COBRE 0.20.0')
        self.assertEqual(r['rotulos_modelos'],['COBRE 0.19.1','COBRE 0.20.0'])
        self.assertEqual(r['totais']['fora'],0);self.assertEqual(r['totais']['sc'],0)
        self.assertTrue(all(all(d==0 for d in row[6]) for row in r['linhas']))
        self.assertEqual(r['usinas'][0],('CAMARGOS',7,107))
        self.assertEqual(r['linhas'][0][2:4],[17,217])
        self.assertTrue(path.exists())

    def test_resultados_sao_os_da_mesma_funcao_sem_intermediacao_numerica(self):
        for row in self.b:
            row['annual_mean_m3s']=100.
            row['ar_coefficient_lag_1']+=.01
        self.gravar_b()
        _,r=self.gerar()
        a=ler_fonte(self.f.novo,'Novo modelo',self.f.deck)
        b=ler_fonte(self.parquet_b,'Novo modelo',self.deck_b)
        original=comparar(a,b)
        for key in ['linhas','totais','campos','tolerancias','datas','usinas']:
            self.assertEqual(r[key],original[key])
        j=r['campos'].index('annual_mean_m3s')
        self.assertEqual(r['linhas'][0][8][j],.01)
        self.assertLess(r['tolerancias'][1],1e-10)  # Nenhuma precisão NEWAVE inventada.
        self.assertGreaterEqual(r['tolerancias'][1],math.ulp(1.054))
        self.assertEqual(r['linhas'][0][7][1],1)
        self.assertNotIn('3 algarismos',str(r['precisao']))

    def test_ordens_diferentes_preservam_valores_e_todos_lags_viram_sc(self):
        for row in self.b:
            if row['hydro_id']==107 and row['stage_id']==217:
                row.update(ar_order=1,ar_coefficient_lag_2=None)
        self.gravar_b();_,r=self.gerar()
        self.assertEqual(r['linhas'][0][7][:3],[1,2,2])
        self.assertEqual(r['linhas'][0][6][1:3],[None,None])
        self.assertEqual(r['linhas'][0][8][1:3],[None,None])
        self.assertEqual(r['linhas'][0][4][1],r['linhas'][0][5][1])
        self.assertGreater(r['tolerancias'][1],0) # O HTML não deve reutilizar este limite global no sc.
        self.assertEqual(r['totais']['sc'],2)

    def test_tipo_origem_calendario_e_nomes_invalidos_bloqueiam(self):
        with self.assertRaisesRegex(ErroConsistencia,'deck correspondente'):
            gerar(self.f.novo,self.parquet_b,self.f.deck,tipo_comparacao='novo_novo')
        with self.assertRaisesRegex(ErroConsistencia,'esquema/precisão'):
            gerar(self.f.novo,self.parquet_b,self.f.deck,progresso=lambda _:None)
        with self.assertRaisesRegex(ErroConsistencia,'nomes diferentes'):
            self.gerar(rotulo_novo='Mesma',rotulo_referencia='mesma')
        d=json.loads((self.deck_b/'stages.json').read_text())
        for e in d['stages']:
            for k in ['start_date','end_date']:e[k]=e[k].replace('2026','2027')
        self.f.salvar_json(self.deck_b/'stages.json',d)
        with self.assertRaisesRegex(ErroConsistencia,'Comparação bloqueada'):self.gerar()

    def test_rotulo_nao_introduz_html_executavel(self):
        path,_=self.gerar(rotulo_novo='</script><img src=x onerror=alert(1)>')
        self.assertNotIn('<img src=x',path.read_text(encoding='utf-8'))
