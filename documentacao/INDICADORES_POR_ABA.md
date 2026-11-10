# Indicadores por aba — regra atual

Atualizado em 09/11/2026: por determinação do usuário, **sc conta como reprovado**.
Esta regra substitui a versão anterior que excluía sc das reprovações e taxas.

## Abas e cartões

O relatório tem oito abas: Visão geral, Ordem PARP, Coeficientes mensais,
Coeficiente anual, Médias mensais, Médias anuais, Desvio padrão mensal e
Desvio padrão anual. Cada detalhe tem filtros independentes e suas estatísticas.

| Grandeza | Campo original |
| --- | --- |
| Médias mensais | `seasonal_mean_m3s` |
| Médias anuais | `annual_mean_m3s` |
| Desvio padrão mensal | `seasonal_std_m3s` |
| Desvio padrão anual | `annual_std_m3s` |

Os campos anuais continuam sendo os da componente anual, por mês do ano;
não são recalculados a partir de vazões de cada ano civil.

Coeficientes mensais tem 12 cartões, Visão geral tem 11 e as demais abas têm 8.
Os três cartões de combinações usina–mês (no recorte, aprovadas e reprovadas)
aparecem somente em Visão geral e Coeficientes mensais. O contador
específico de **Sem comparação (sc)** aparece somente em Coeficientes mensais.
Também não há contador/coluna separado de sc na Visão geral. Isso não retira
sc dos totais gerais de reprovação ou das taxas.

| Indicador | Definição |
| --- | --- |
| Combinações usina–mês no recorte, somente em Visão geral e Coeficientes mensais | Pares distintos presentes nas linhas filtradas. |
| Usinas no recorte | Usinas distintas presentes nas linhas filtradas. |
| Grandezas avaliadas | Dentro da tolerância + fora da tolerância + sc. |
| Combinações usina–mês aprovadas, somente em Visão geral e Coeficientes mensais | Pares com todas as grandezas dentro da tolerância; nenhum fora ou sc no recorte. |
| Usinas aprovadas no recorte | Usinas com todas as grandezas dentro da tolerância; nenhum fora ou sc no recorte. |
| Taxa de aprovação | Dentro / (dentro + fora + sc) × 100. |
| Grandezas aprovadas | Quantidade dentro da tolerância. |
| Combinações usina–mês reprovadas, somente em Visão geral e Coeficientes mensais | Pares com pelo menos um fora da tolerância ou sc no recorte. |
| Usinas com ao menos um mês reprovado | Usinas com pelo menos um fora da tolerância ou sc no recorte. |
| Taxa de reprovação | (Fora + sc) / (dentro + fora + sc) × 100. |
| Grandezas reprovadas | Fora da tolerância + sc. |
| Sem comparação (sc), somente em Coeficientes mensais | Parcela dos reprovados correspondente aos lags ativos de ajustes com ordens diferentes, inclusive lags comuns. Já incluída nos totais; não somar novamente. |

Cada usina e combinação é contada uma vez nos respectivos cartões. Grandezas
(lags ou campos) são contadas individualmente. Um grupo misto, com aprovação
e qualquer fora ou sc, é reprovado. Grupos somente sc são reprovados, com taxa
de reprovação de 100% e de aprovação de 0%. As contagens de aprovados e reprovados
somam o total avaliado, sem duplicar sc.

Sem linhas no recorte, ambas as taxas aparecem como **—**. Lags inativos nas
duas fontes continuam ausentes das tabelas e das contagens; não são sc.

## Filtros e resumos

Nas sete abas de detalhe, cartões e tabela usam todas as linhas após os filtros
gerais, Resultado e cabeçalhos, antes da paginação. Ordenação e mudança de página
não alteram as estatísticas. Filtros locais são preservados por aba na sessão.
Na Visão geral, cartões e resumos seguem os filtros gerais de usina e intervalo.

Resultado oferece **Reprovados (fora + sc)**. Os filtros individuais de fora da
tolerância e sc continuam disponíveis, preservando a distinção entre os motivos.
Filtrar somente aprovados ou reprovados produz 100% na respectiva taxa quando
houver linhas. O contador de sc mostra a quantidade no recorte ativo da aba mensal.

Os resumos da Visão geral exibem Avaliados, Aprovados, Reprovados (fora + sc) e
Aprovação (%). As reprovações incluem sc também por tipo, usina e mês do ano.

## Valores preservados

Sc continua identificado como sc nas linhas, com o coeficiente ausente e a
diferença ausente. A nova regra altera a agregação de reprovações, não inventa
coeficientes, não preenche zeros e não modifica as tolerâncias numéricas.
Os três resultados técnicos originais permanecem distinguíveis no JSON:
dentro, fora e sc. Os totais técnicos `comparaveis`, `fora` e `sc` preservam
essa discriminação; a reprovação apresentada é calculada como fora + sc.
Os dados incorporados dos dois HTMLs foram preservados integralmente.

## Verificação

- 41 testes Python aprovados.
- Auditor de indicadores: 116 conferências por modo (232 no total), nas oito abas,
  incluindo filtro conjunto de reprovados, apenas sc, grupos mistos, recortes
  vazios, filtros combinados, paginação e layout de 390 pixels. Confere também
  a ausência dos três cartões de combinações nas outras seis abas.
- Auditor de tabelas: resumos gerais conferidos com sc incluído nas reprovações
  e denominadores; ausência de contador específico de sc fora da aba mensal.
- Asserções de que aprovados + reprovados = avaliados, inclusive para combinações
  e usinas, sem dupla contagem. Payloads preservados, sem requisições externas.

No relatório real Novo modelo × NEWAVE, em Coeficientes mensais sem filtros
adicionais: 618 fora + 457 sc = **1075 reprovados**, sobre 3614 avaliados;
taxa de reprovação de **29,75%**, 454 combinações e 144 usinas com reprovação.
Na Visão geral: 1877 fora + 457 sc = **2334 reprovados**, sobre 15062 avaliados;
taxa de reprovação de **15,50%**. Os números não são fixados no programa.

Evidências e capturas: `outputs/verificacao/indicadores/`. Relatórios atualizados:
`relatorios/comparacao_mensal_novo_newave_filtros.html` e
`relatorios/comparacao_mensal_novo_novo_filtros.html`. As próximas gerações
pelo `.bat` já incluem a regra. Os insumos foram preservados.
