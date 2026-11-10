# Plano — comparação de parâmetros por usina e mês do ano

Data: 08/11/2026.

## Estado e objetivo

Implementado e verificado em 08/11/2026. O comparador, as contagens e o HTML agora usam a unidade usina/mês do ano, após validar todos os anos. As verificações realizadas constam da seção 7. Este documento prevalece sobre descrições anteriores que tratem cada mês/ano como uma comparação independente.

Validar todos os cenários e todos os anos dos arquivos de entrada, mas comparar as fontes e apresentar os resultados apenas uma vez por usina e mês do ano. Em um horizonte com os 12 meses representados, cada usina terá 12 conjuntos mensais de comparação, independentemente da quantidade de anos e cenários.

A mudança aplica-se aos dois modos existentes: Novo modelo × NEWAVE e Novo modelo × Novo modelo. Todas as grandezas, fórmulas, tolerâncias e classificações atuais permanecem.

## 1. Grandezas de cada conjunto mensal

Cada conjunto representa uma usina e um mês do ano e contém todos os campos atuais:

| Grandeza | Campo |
| --- | --- |
| Ordem ajustada PARP | `ar_order` |
| Coeficiente autorregressivo do lag 1 | `ar_coefficient_lag_1` |
| Coeficiente autorregressivo do lag 2 | `ar_coefficient_lag_2` |
| Coeficiente autorregressivo do lag 3 | `ar_coefficient_lag_3` |
| Coeficiente autorregressivo do lag 4 | `ar_coefficient_lag_4` |
| Coeficiente autorregressivo do lag 5 | `ar_coefficient_lag_5` |
| Coeficiente autorregressivo do lag 6 | `ar_coefficient_lag_6` |
| Coeficiente da componente anual | `annual_coefficient` |
| Média da componente anual | `annual_mean_m3s` |
| Desvio padrão da componente anual | `annual_std_m3s` |
| Média mensal do ajuste | `seasonal_mean_m3s` |
| Desvio padrão mensal do ajuste | `seasonal_std_m3s` |

Com seis lags disponíveis, são 12 campos por conjunto mensal. A quantidade de lags continua identificada pelos arquivos: seis não será uma constante nova do programa.

A componente anual também permanece discriminada por mês do ano, conforme os parâmetros armazenados. Não substituí-la por uma média ou desvio das vazões de um ano civil.

Ter 12 conjuntos mensais não significa ter somente 12 comparações individuais por usina: cada conjunto contém as grandezas acima, respeitando a ativação dos lags.

## 2. Validação antes da consolidação

1. Manter as validações atuais de esquema, origem, cadastro, calendário, grade, valores finitos, ordens, lags e constância entre cenários da mesma usina e estágio.
2. Manter o pareamento entre fontes por nome normalizado da usina e pelo mesmo mês e ano. A consolidação não poderá fazer arquivos com horizontes incompatíveis parecerem correspondentes.
3. Em cada fonte, separadamente, agrupar os estágios por usina e mês do ano. Comparar todos os campos do conjunto entre todos os anos presentes, sem aplicar filtros da interface antes dessa validação.
4. Exigir igualdade exata dos valores armazenados entre anos. As tolerâncias usadas para comparar A com B não servem para autorizar diferenças internas entre anos. Não arredondar antes de conferir.
5. Verificar também a presença ou ausência dos lags: ordem e atividade precisam ser constantes naquele mês entre os anos. Nulos dos lags inativos devem continuar nulos; as validações atuais de nulos permanecem.
6. Somente após todas as verificações aprovarem, consolidar um único conjunto por usina e mês do ano em cada fonte e comparar A com B.

Se qualquer grandeza de um mês variar entre anos dentro de uma fonte, bloquear a geração inteira e identificar a fonte, a usina, o mês, o campo, os anos e os valores divergentes. Preservar o relatório anterior.

É proibido escolher silenciosamente o primeiro ou o último ano, calcular uma média entre anos, usar maioria, arredondar, preencher zeros, descartar anos ou substituir valores para permitir a consolidação. Depois de comprovada a igualdade integral, conservar o valor original comum é permitido; isso não envolve estimativa ou correção.

Para horizontes parciais, manter as regras atuais de calendário e grade: usar apenas os meses efetivamente observados e validados. Não criar meses ou valores ausentes para completar 12 conjuntos. Com menos de dois anos para um mês, registrar que não há repetição entre anos a conferir naquele grupo.

## 3. Comparação entre fontes e contagens

A unidade passa a ser `(usina, mês do ano, campo)`, incluindo o lag quando aplicável. Cada unidade entra no resultado apenas uma vez, independentemente da quantidade de anos ou cenários.

Permanecem as regras atuais:

- Diferença absoluta: `|A - B|`.
- Ordem PARP: comparação exata.
- Coeficientes mensais e anual: tolerâncias globais por tipo, conforme a precisão real das fontes e considerando todos os dados antes de filtros.
- Médias e desvios: percentual escolhido pelo usuário sobre `|B|`; referência zero implica tolerância zero.
- Limite inclusivo e cálculo com `Decimal`, conforme a implementação atual.
- Lags ativos nas duas fontes: comparar, inclusive quando o coeficiente ativo vale zero.
- Lag ativo em apenas uma fonte: classificar como `sc`, com valor e motivo.
- Lag inativo nas duas fontes: não comparar nem contar.
- Coeficiente ativo ausente: erro de consistência.

Somar comparáveis, dentro da tolerância, fora da tolerância e `sc` a partir dos conjuntos consolidados. Uma diferença em janeiro presente nos seis anos será contada uma vez para aquela usina e campo. Duas grandezas fora da tolerância em janeiro serão duas divergências, mesmo pertencendo ao mesmo conjunto mensal.

O percentual Dentro (%) permanece `dentro / (dentro + fora) × 100`, excluindo `sc`. Não multiplicar contagens pela quantidade de anos ou cenários. Os totais, os resumos e as tabelas de detalhe precisam usar a mesma base consolidada; ocultar linhas repetidas apenas na tela não atende ao pedido.

## 4. HTML e filtros

Manter as cinco abas atuais e todas as grandezas de cada uma. Exibir Janeiro a Dezembro em ordem cronológica nas comparações, substituindo o mês/ano da identificação das linhas por mês do ano.

A visão geral terá contagens consolidadas por tipo, por usina e por mês do ano. O horizonte original, as fontes e a confirmação de constância entre anos permanecerão disponíveis como informações de rastreabilidade, sem gerar comparações adicionais.

Preservar busca por usina, ordenação, paginação, filtro de resultado, unidades, ordens nas colunas atuais, apresentação numérica e barras de rolagem. Manter o intervalo de mês/ano como recorte do horizonte original: um conjunto mensal aparece quando existe pelo menos uma ocorrência desse mês no intervalo selecionado. Mesmo com várias ocorrências no intervalo, o conjunto e suas contagens aparecem uma única vez. A validação de todos os anos ocorre antes desse filtro, e as tolerâncias globais não mudam.

Preservar o HTML único offline, os seletores de fontes/decks, os rótulos das versões, a referência B e a proteção do relatório anterior em caso de falha. Não acrescentar gráficos, análises estatísticas ou exportações nesta mudança.

## 5. Evidência disponível

A conferência registrada em `outputs/verificacao/repeticao_mensal_2026_11_08/resultado.json` verificou os Parquets atuais de COBRE 0.19.1, COBRE 0.20 e NEWAVE.

Cada fonte tem 159 usinas, 72 meses de janeiro/2026 a dezembro/2031 e 22896000 linhas. Todos os 12 campos se repetem exatamente para a mesma usina e mês do ano nos seis anos, inclusive os nulos dos lags inativos. Foram 114480 verificações entre anos por fonte, totalizando 343440, sem divergências.

Nesses arquivos, os 11448 pares usina-estágio de cada fonte correspondem a 1908 conjuntos usina-mês do ano (`159 × 12`). Esses números descrevem o estudo conferido e não serão fixados no código. Esta evidência não dispensa validar novos arquivos em cada geração.

## 6. Implementação e aceite previstos

A implementação deverá contemplar `comparador/dados.py`, a organização das comparações e dos totais em `comparador/regras.py`, os dados incorporados ao HTML e os recursos de interface correspondentes. A mudança da unidade de contagem não autoriza alterar as fórmulas numéricas.

Validar a implementação com os testes existentes e verificações específicas da nova regra:

- Repetições exatas entre cenários e anos produzem um conjunto por usina e mês do ano, conservando todos os campos.
- Alteração de qualquer campo entre anos, inclusive pequena diferença ou mudança de atividade de lag, bloqueia a geração e informa os valores reais.
- Diferenças reais entre A e B continuam presentes e são contadas uma vez por usina, mês e campo; várias grandezas diferentes continuam contadas separadamente.
- Horizontes incompatíveis continuam bloqueados; meses ausentes nunca são fabricados.
- Tolerâncias, zeros ativos, lags inativos, `sc`, limites e percentuais permanecem corretos.
- Filtros, resumos e tabelas usam a mesma base mensal sem multiplicar as contagens pelos anos.
- Conferência dos arquivos reais e inspeção do HTML nos dois modos de comparação, sem modificar os insumos.

Atualizar a documentação e os auditores afetados quando a implementação for realizada. Não considerar a mudança concluída apenas pela criação deste plano.

## 7. Implementação e verificações realizadas

- `comparador/dados.py`: nova consolidação com igualdade exata para cada campo entre anos, incluindo ordem, componente anual e lags nulos. Erros identificam arquivo/fonte, usina, mês, campo, datas e valores.
- `comparador/regras.py`: conserva o pareamento completo e as funções numéricas; valida as duas fontes antes de comparar os conjuntos mensais. Formato interno versão 4, com `unidade_comparacao=usina_mes_do_ano`, `meses` para as linhas consolidadas e `datas` para o horizonte original e os filtros. As fontes registram anos por mês, quantidade de conjuntos e grupos com/sem repetição entre anos.
- HTML/JavaScript: cinco abas preservadas, identificação por mês do ano, resumos e detalhes na mesma base consolidada. O intervalo original filtra os meses com ocorrência sem duplicar as linhas; tolerâncias e validações não são recalculadas pelos filtros.
- `python -m testes`: 41 testes aprovados, incluindo os 33 existentes e oito novos testes de consolidação, com verificações de cada campo nas duas fontes, diferenças mínimas, preservação de saída em falha, lags e horizontes parciais.
- Auditoria independente dos Parquets e das contas nos dois modos; auditor de tabelas JavaScript com oito seleções por relatório, incluindo o segundo ano, um único mês e virada de ano.
- Verificação em Chrome dos dois relatórios reais: cinco abas, meses em ordem, filtros, paginação, filtro de resultado, unidade à direita e rolagem sincronizada; nenhuma exceção JavaScript ou requisição externa. Capturas de tela salvas e inspecionadas.

Resultados reais após remover as seis repetições anuais:

| Modo e percentual usado na conferência | Conjuntos usina/mês | Comparáveis | Dentro | Fora | sc |
| --- | --- | --- | --- | --- | --- |
| COBRE 0.20 × COBRE 0.19.1, 0% | 1908 | 14711 | 14711 | 0 | 0 |
| COBRE 0.20 × NEWAVE, 1% | 1908 | 14605 | 12728 | 1877 | 457 |

Os percentuais acima reproduzem os relatórios anteriores para a conferência; não são novos valores padrão ou recomendações. A preferência local do usuário não foi alterada.

Cada novo resultado foi confrontado com todas as linhas correspondentes do relatório anterior: valores A/B, diferenças absolutas, classificações e tolerâncias idênticos. Cada contagem antiga equivale exatamente a seis vezes a nova, por repetição dos seis anos, sem eliminar divergências reais. Foram conferidas 45792000 linhas de entrada por modo.

Relatórios novos: `relatorios/comparacao_mensal_novo_novo.html` e `relatorios/comparacao_mensal_novo_newave.html`. Os relatórios antigos foram preservados. Evidências em `outputs/verificacao/consolidacao_mensal/`: `auditoria_dados_reais.json`, `conferencia_relatorios_anteriores.json` e, na subpasta de cada relatório, `tabelas.json`, `navegador.json` e capturas de tela.

Não foram alterados os Parquets, decks ou valores dos estudos. Não houve commit ou publicação.
