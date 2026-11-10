from decimal import Decimal
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pyarrow as pa
import pyarrow.parquet as pq

from comparador.dados import ErroConsistencia, ler_fonte, parear
from comparador.executar import gerar
from comparador.regras import comparar, comparar_valores, precisao_newave, tolerancia_valor, MOMENTOS
from comparador.relatorio import salvar_html


class ComparadorTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.pasta = Path(self.tmp.name)
        self.deck = self.pasta / "deck"
        (self.deck / "system").mkdir(parents=True)
        self.salvar_json(self.deck / "system/hydros.json", {"hydros":[{"id":7,"name":"CAMARGOS"},{"id":8,"name":"FURNAS"}]})
        self.salvar_json(self.deck / "stages.json", {"stages":[
            {"id":17,"start_date":"2026-08-01","end_date":"2026-09-01"},
            {"id":18,"start_date":"2026-09-01","end_date":"2026-10-01"}]})
        self.meta = {b"source_model":b"NEWAVE",b"newave_schema_version":b"2",
                     b"coefficient_basis":b"seasonal_standardized",b"ar_max_order":b"2",
                     b"hydro_mapping":json.dumps([{"hydro_id":90,"nome_usina_cadastro":"Camargos"},
                                                  {"hydro_id":91,"nome_usina_cadastro":"FURNAS"}]).encode(),
                     b"stage_mapping":json.dumps([
                         {"stage_id":0,"start_date":"2026-08-01","end_date":"2026-09-01"},
                         {"stage_id":1,"start_date":"2026-09-01","end_date":"2026-10-01"}]).encode()}
        self.a, self.b = [], []
        for h in range(2):
            for s in range(2):
                for c in range(3):
                    base = dict(scenario_id=c, hydro_id=7+h, stage_id=17+s, ar_order=2,
                                ar_coefficient_lag_1=.393309, ar_coefficient_lag_2=.21,
                                annual_coefficient=.1281, annual_mean_m3s=127.624,
                                annual_std_m3s=36.98, seasonal_mean_m3s=242.03, seasonal_std_m3s=103.66)
                    self.a.append(base)
                    nw = dict(base,hydro_id=90+h,stage_id=s,ar_coefficient_lag_1=.393,
                              annual_coefficient=.128,annual_mean_m3s=127.62)
                    if h == 0 and s == 0:
                        nw.update(ar_order=1,ar_coefficient_lag_2=None)
                    if h == 1 and s == 1:
                        base["ar_coefficient_lag_1"] = 1.054
                        nw["ar_coefficient_lag_1"] = 1.05
                        base["ar_coefficient_lag_2"] = nw["ar_coefficient_lag_2"] = 0.
                    self.b.append(nw)
        self.novo, self.nw = self.pasta/"novo.parquet", self.pasta/"newave.parquet"
        self.gravar()

    def salvar_json(self, caminho, dados):
        caminho.write_text(json.dumps(dados), encoding="utf-8")

    def gravar(self):
        campos = list(self.a[0])
        schema = pa.schema([pa.field(c,pa.int64() if c in ("scenario_id","hydro_id","stage_id","ar_order") else pa.float64()) for c in campos])
        pq.write_table(pa.Table.from_pylist(self.a,schema=schema),self.novo)
        pq.write_table(pa.Table.from_pylist(self.b,schema=schema.with_metadata(self.meta)),self.nw)

    def fontes(self):
        return ler_fonte(self.novo,"Novo modelo",self.deck),ler_fonte(self.nw,"NEWAVE")

    def test_pareia_por_nome_data_com_ids_diferentes_e_inicio_em_agosto(self):
        a,b = self.fontes()
        resultado=comparar(a,b)
        self.assertEqual(resultado["usinas"][0],("CAMARGOS",7,90))
        self.assertEqual(resultado["datas"],["2026-08","2026-09"])
        self.assertEqual(len(resultado["linhas"]),4)
        self.assertEqual(resultado["linhas"][0][2:4],[17,0])
        self.assertEqual(a.registros,12)

    def test_ordens_diferentes_tornam_lag_comum_e_lag_ausente_sc(self):
        r=comparar(*self.fontes());p=r["linhas"][0]
        self.assertEqual(p[7][0],1) # Ordem diferente.
        self.assertEqual(p[7][1],2) # Mesmo o lag comum não pode ser comparado.
        self.assertEqual(p[7][2],2) # Lag 2 ativo somente no novo modelo.
        self.assertIsNone(p[5][2])
        self.assertIsNone(p[8][2])
        self.assertEqual(p[4][1],.393309)
        self.assertEqual(p[5][1],.393)
        self.assertEqual(p[6][1:3],[None,None])
        self.assertEqual(p[8][1:3],[None,None])
        self.assertEqual(r["totais"]["sc"],2)

    def test_ordens_diferentes_em_ambas_as_direcoes_inclusive_ordem_zero(self):
        for ordem_a,ordem_b in ((2,1),(1,2),(2,0),(0,2)):
            with self.subTest(ordem_a=ordem_a,ordem_b=ordem_b):
                a,b=self.fontes()
                for valores,ordem in ((a.parametros[7,17],ordem_a),(b.parametros[90,0],ordem_b)):
                    valores['ar_order']=ordem
                    for lag in (1,2):
                        valores[f'ar_coefficient_lag_{lag}']=0. if lag<=ordem else None
                r=comparar(a,b);p=r['linhas'][0]
                self.assertEqual(p[7][1:3],[2,2])
                self.assertEqual(p[6][1:3],[None,None])
                self.assertEqual(p[8][1:3],[None,None])
                self.assertEqual(r['totais']['sc'],max(ordem_a,ordem_b))
                for i in (1,2):
                    self.assertEqual(p[4][i],a.parametros[7,17][r['campos'][i]])
                    self.assertEqual(p[5][i],b.parametros[90,0][r['campos'][i]])
                # Ordem reprova; anual e quatro estatísticas mantêm suas comparações.
                self.assertEqual(p[7][0],1)
                self.assertEqual(p[7][3:],[0]*5)

    def test_zero_ativo_nao_e_ausencia(self):
        r=comparar(*self.fontes());p=r["linhas"][-1]
        self.assertEqual(p[4][2],0.)
        self.assertEqual(p[7][2],0)

    def test_coeficientes_usam_tolerancia_por_valor_newave_e_estatisticas_fixa(self):
        r=comparar(*self.fontes())
        self.assertEqual(r["tolerancias"][0],0.)
        self.assertEqual(r["tolerancias"][1:4],[None]*3)
        self.assertEqual(r["tolerancias"][4:], [.01]*4)
        self.assertIsNone(r["linhas"][0][8][1])
        self.assertEqual(r["linhas"][1][8][1], .001)
        self.assertEqual(r["linhas"][-1][8][1], .01)
        self.assertEqual(r["linhas"][0][8][3], .001)
        self.assertEqual(r["linhas"][0][8][4], .01)

    def test_coeficientes_seguem_expoente_newave_por_usina_mes_lag_e_anual(self):
        a,b=self.fontes()
        b.parametros[90,0].update(ar_order=2,ar_coefficient_lag_2=.21)
        a.parametros[7,17]["ar_coefficient_lag_1"] = .394
        a.parametros[7,18]["ar_coefficient_lag_1"] = .039401
        b.parametros[90,1]["ar_coefficient_lag_1"] = .0393
        a.parametros[8,17]["ar_coefficient_lag_1"] = -.00394
        b.parametros[91,0]["ar_coefficient_lag_1"] = -.00393
        a.parametros[7,18]["ar_coefficient_lag_2"] = .0003941
        b.parametros[90,1]["ar_coefficient_lag_2"] = .000393
        a.parametros[7,18]["annual_coefficient"] = .0012901
        b.parametros[90,1]["annual_coefficient"] = .00128
        r=comparar(a,b)
        self.assertEqual([p[8][1] for p in r["linhas"]],[.001,.0001,.00001,.01])
        self.assertEqual([p[7][1] for p in r["linhas"]],[0,1,0,0])
        self.assertEqual(r["linhas"][1][8][2],.000001)
        self.assertEqual(r["linhas"][1][7][2],1)
        self.assertEqual(r["linhas"][1][8][3],.00001)
        self.assertEqual(r["linhas"][1][7][3],1)
        # Outro coeficiente grande e a escala do COBRE não ampliam os limites locais.
        a.parametros[8,18]["ar_coefficient_lag_1"] = 1000.
        b.parametros[91,1]["ar_coefficient_lag_1"] = 1000.
        a.parametros[7,18]["ar_coefficient_lag_1"] = 100.
        s=comparar(a,b)
        self.assertEqual(s["linhas"][1][8][1],.0001)
        self.assertEqual(s["linhas"][1][7][1],1)

    def test_precisao_coeficientes_zero_potencias_de_dez_e_limites_inclusivos(self):
        for campo in ("ar_coefficient_lag_1","annual_coefficient"):
            for valor, limite in ((0.,".001"),(.1,".001"),(.01,".0001"),(1.,".01"),(-.0393,".0001")):
                with self.subTest(campo=campo,valor=valor):
                    tolerancia=tolerancia_valor(campo,valor,"NEWAVE")
                    self.assertEqual(tolerancia,Decimal(limite))
                    for sinal in (-1,1):
                        fronteira=Decimal(str(valor))+sinal*Decimal(limite)
                        self.assertEqual(comparar_valores(fronteira,valor,tolerancia)[1],0)
                        self.assertEqual(comparar_valores(fronteira+sinal*Decimal("1e-10"),valor,tolerancia)[1],1)

    def test_limite_inclusivo_decimal_e_diferenca_absoluta(self):
        self.assertEqual(comparar_valores(.1,.095,Decimal(".005")),(.005,0))
        self.assertEqual(comparar_valores(.095,.1,Decimal(".005")),(.005,0))
        self.assertEqual(comparar_valores(.100001,.095,Decimal(".005"))[1],1)
        self.assertEqual(precisao_newave("annual_coefficient",1.05),Decimal(".01"))
        self.assertEqual(precisao_newave("annual_coefficient",.393),Decimal(".001"))

    def test_coeficientes_usam_precisao_inteira_e_estatisticas_limite_fixo(self):
        self.assertEqual(tolerancia_valor("ar_coefficient_lag_1",1.05,"NEWAVE"),Decimal(".01"))
        self.assertEqual(tolerancia_valor("annual_coefficient",1.05,"NEWAVE"),Decimal(".01"))
        self.assertEqual(tolerancia_valor("annual_coefficient",0.,"NEWAVE"),Decimal(".001"))
        self.assertEqual(tolerancia_valor("seasonal_mean_m3s",1.05,"NEWAVE"),Decimal(".01"))
        self.assertEqual(tolerancia_valor("seasonal_mean_m3s",0.,"Novo modelo"),Decimal(".01"))
        self.assertEqual(comparar_valores(1.06,1.05,Decimal(".01")),(.01,0))
        self.assertEqual(comparar_valores(1.060001,1.05,Decimal(".01"))[1],1)

    def test_tolerancia_fixa_independe_de_usina_estagio_e_magnitude(self):
        a,b=self.fontes()
        b.parametros[90,0]["annual_mean_m3s"]=100.
        b.parametros[90,1]["annual_mean_m3s"]=1000.
        b.parametros[91,0]["annual_mean_m3s"]=200.
        r=comparar(a,b)
        for campo in MOMENTOS:
            j=r["campos"].index(campo)
            self.assertEqual([p[8][j] for p in r["linhas"]],[.01]*4)
        self.assertNotIn("percentual_estatisticas",r)
        self.assertEqual(r["tolerancia_estatisticas_m3s"],.01)
        self.assertEqual(r["criterio_estatisticas"],"absoluta_fixa_0_01_m3s")

    def test_estatisticas_aprovam_limites_positivos_e_negativos_e_reprovam_excesso(self):
        a,b=self.fontes()
        for referencia in ("0","0.01","100000","-100"):
            for delta in ("0.01","-0.01","0.010001","-0.010001"):
                with self.subTest(referencia=referencia,delta=delta):
                    campos=MOMENTOS if Decimal(referencia)>0 or (Decimal(referencia)==0 and Decimal(delta)>0) else {"annual_mean_m3s","seasonal_mean_m3s"}
                    for campo in campos:
                        a.parametros[7,17][campo]=float(Decimal(referencia)+Decimal(delta))
                        b.parametros[90,0][campo]=float(referencia)
                    r=comparar(a,b)
                    for campo in campos:
                        j=r["campos"].index(campo)
                        self.assertEqual(r["linhas"][0][7][j],0 if abs(Decimal(delta))<=Decimal(".01") else 1)

    def test_valores_e_diferencas_preservados_sem_arredondamento(self):
        a,b=self.fontes()
        a.parametros[7,17]["annual_mean_m3s"]=127.630001
        r=comparar(a,b)
        j=r["campos"].index("annual_mean_m3s")
        self.assertEqual(r["linhas"][0][4][j],127.630001)
        self.assertEqual(r["linhas"][0][5][j],127.62)
        self.assertEqual(r["linhas"][0][6][j],.010001)
        self.assertEqual(r["linhas"][0][7][j],1)

    def test_geracao_nao_exige_percentual_e_html_informa_limite_fixo(self):
        saida,r=gerar(self.novo,self.nw,self.deck,self.pasta/"fixo.html",progresso=lambda _:None)
        self.assertTrue(saida.exists())
        self.assertEqual(r["criterio_estatisticas"],"absoluta_fixa_0_01_m3s")
        self.assertIn("Tolerância absoluta fixa de 0,01 m³/s",saida.read_text(encoding="utf-8"))

    def test_coeficiente_entre_meia_unidade_e_unidade_inteira_esta_dentro(self):
        for r in self.a:
            if r["hydro_id"]==8 and r["stage_id"]==18:
                r["ar_coefficient_lag_1"]=1.058
        self.gravar()
        r=comparar(*self.fontes())
        self.assertEqual(r["linhas"][-1][6][1],.008)
        self.assertEqual(r["linhas"][-1][7][1],0)

    def test_parametro_varia_no_ultimo_cenario_bloqueia(self):
        self.a[-1]["annual_mean_m3s"]+=1
        self.gravar()
        with self.assertRaisesRegex(ErroConsistencia,"varia entre cenários"):
            self.fontes()

    def test_nulos_parciais_e_parametro_ativo_ausente_bloqueiam(self):
        self.a[-1]["ar_coefficient_lag_1"]=None
        self.gravar()
        with self.assertRaisesRegex(ErroConsistencia,"nulos parciais"):
            self.fontes()
        for r in self.a:
            r["ar_coefficient_lag_1"]=None
        self.gravar()
        with self.assertRaisesRegex(ErroConsistencia,"ativo ausente"):
            self.fontes()

    def test_lag_inativo_nao_pode_conter_zero(self):
        for r in self.b:
            if r["hydro_id"]==90 and r["stage_id"]==0:
                r["ar_coefficient_lag_2"]=0.
        self.gravar()
        with self.assertRaisesRegex(ErroConsistencia,"inativo não nulo"):
            self.fontes()

    def test_lags_inativos_nos_dois_nao_contam_sc(self):
        for r in self.a+self.b:
            r.update(ar_order=0,ar_coefficient_lag_1=None,ar_coefficient_lag_2=None)
        self.gravar()
        r=comparar(*self.fontes())
        self.assertEqual(r["totais"]["sc"],0)
        self.assertEqual(r["totais"]["comparaveis"],4*6)

    def test_grade_combinacoes_incompleta_bloqueia(self):
        self.b=[r for r in self.b if not(r["hydro_id"]==91 and r["stage_id"]==1)]
        self.gravar()
        with self.assertRaisesRegex(ErroConsistencia,"grade incompleta"):
            self.fontes()

    def test_ano_diferente_nao_e_comparavel_mesmo_mesmo_mes(self):
        a,b=self.fontes()
        b.datas={s:d.replace(year=2027) for s,d in b.datas.items()}
        with self.assertRaisesRegex(ErroConsistencia,"Comparação bloqueada"):
            parear(a,b)

    def test_virada_de_ano_preserva_pareamento_sem_usar_id(self):
        a,b=self.fontes()
        from datetime import date
        a.datas={17:date(2026,12,1),18:date(2027,1,1)}
        b.datas={0:date(2026,12,1),1:date(2027,1,1)}
        r=comparar(a,b)
        self.assertEqual(r["datas"],["2026-12","2027-01"])
        self.assertEqual(len(r["linhas"]),4)

    def test_limite_de_lags_diferente_e_dinamico(self):
        a,b=self.fontes()
        a.colunas.insert(3,"ar_coefficient_lag_3")
        for valores in a.parametros.values():
            valores["ar_order"]=3
            valores["ar_coefficient_lag_3"]=.1
        r=comparar(a,b)
        j=r["campos"].index("ar_coefficient_lag_3")
        self.assertTrue(all(p[7][j]==2 for p in r["linhas"]))

    def test_calendario_de_mais_de_um_mes_bloqueia(self):
        d=json.loads((self.deck/"stages.json").read_text())
        d["stages"][0]["end_date"]="2026-10-01"
        self.salvar_json(self.deck/"stages.json",d)
        with self.assertRaisesRegex(ErroConsistencia,"intervalo mensal inválido"):
            self.fontes()

    def test_usina_sem_correspondente_bloqueia(self):
        a,b=self.fontes();b.nomes[90]="OUTRA UHE"
        with self.assertRaisesRegex(ErroConsistencia,"ausente"):
            parear(a,b)

    def test_calendario_e_nomes_ambiguos_bloqueiam(self):
        self.salvar_json(self.deck/"system/hydros.json",{"hydros":[{"id":7,"name":"CAMARGOS"},{"id":8,"name":"Cámargos"}]})
        with self.assertRaisesRegex(ErroConsistencia,"ambíguo"):
            self.fontes()

    def test_nao_finito_e_desvio_negativo_bloqueiam(self):
        for r in self.a:
            r["annual_std_m3s"]=-1.
        self.gravar()
        with self.assertRaisesRegex(ErroConsistencia,"desvio negativo"):
            self.fontes()
        for r in self.a:
            r["annual_std_m3s"]=float("nan")
        self.gravar()
        with self.assertRaisesRegex(ErroConsistencia,"não é finito"):
            self.fontes()

    def test_perfil_newave_desconhecido_bloqueia(self):
        self.meta[b"newave_schema_version"]=b"99"
        self.gravar()
        with self.assertRaisesRegex(ErroConsistencia,"precisão não reconhecidos"):
            self.fontes()

    def test_html_independente_seguro_com_todos_os_dados(self):
        r=comparar(*self.fontes())
        r["usinas"][0]=("</script><img src=x onerror=alert(1)>",7,90)
        saida=salvar_html(r,self.pasta/"resultado.html")
        texto=saida.read_text(encoding="utf-8")
        self.assertNotIn("<img src=x",texto)
        self.assertNotIn("<script src=",texto)
        self.assertNotIn("__DADOS_JSON__",texto)
        self.assertEqual(texto.count('role="tab"'),8)
        for aba in ('medias_mensais', 'medias_anuais', 'desvio_mensal', 'desvio_anual'):
            self.assertIn(f'data-tab="{aba}"', texto)
        self.assertNotIn('data-tab="estatisticas"', texto)
        inicio=texto.index('<script id="dados" type="application/json">')+len('<script id="dados" type="application/json">')
        dados=json.loads(texto[inicio:texto.index("</script>",inicio)])
        self.assertEqual(len(dados["linhas"]),4)
        self.assertEqual(dados["usinas"][0][0],r["usinas"][0][0])

    def test_falha_preserva_relatorio_anterior(self):
        destino=self.pasta/"anterior.html";destino.write_text("anterior",encoding="utf-8")
        r=comparar(*self.fontes())
        with patch("comparador.relatorio.os.replace",side_effect=OSError("falha simulada")):
            with self.assertRaises(OSError):
                salvar_html(r,destino)
        self.assertEqual(destino.read_text(),"anterior")
        self.assertFalse(list(self.pasta.glob("*.tmp")))

    def test_pipeline_gera_e_inconsistencia_preserva_saida(self):
        destino=self.pasta/"resultado.html"
        _,r=gerar(self.novo,self.nw,self.deck,destino,progresso=lambda _:None)
        self.assertEqual(r["totais"]["pares"],4)
        antes=destino.read_bytes()
        self.a[-1]["annual_coefficient"]+=1
        self.gravar()
        with self.assertRaises(ErroConsistencia):
            gerar(self.novo,self.nw,self.deck,destino,progresso=lambda _:None)
        self.assertEqual(destino.read_bytes(),antes)


if __name__ == "__main__":
    unittest.main()
