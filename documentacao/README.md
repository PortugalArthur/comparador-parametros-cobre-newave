# Comparador de parâmetros — novo modelo × NEWAVE

**Retomada em outro chat:** leia [CONTEXTO_PARA_RETOMADA.md](CONTEXTO_PARA_RETOMADA.md),
atualizado em 09/11/2026, com decisões, regras atuais, auditorias reais e limites conhecidos.

**Tolerâncias vigentes, 09/11/2026:** coeficientes mensais e anual usam
`0,001 × 10^e`, com o expoente do formato NEWAVE `0.XXXE±YY`, individualmente
por usina, mês e coeficiente. Médias e desvios mensais e anuais usam **0,01 m³/s
fixo**, inclusive para referência zero, nos dois modos. O campo e o argumento
de percentual foram removidos. Na comparação de dois COBRE, os coeficientes
mantêm o limite global por tipo baseado nos float64 das fontes.

**Atualização de 06/11/2026:** a janela também permite **Novo modelo × Novo modelo**,
com identificação das versões e seleção do deck de cada fonte. Cada fonte permite indicar a versão utilizada. Consulte [Comparação entre versões](COMPARACAO_ENTRE_VERSOES.md)
para as entradas e a aplicação da regra de precisão a dois arquivos COBRE.

Programa independente do avaliador de testes estatísticos. Lê os parâmetros enriquecidos dos dois modelos e produz um único HTML com oito abas, exclusivamente com tabelas. O HTML funciona localmente, sem internet nem instalação de um servidor.

**Atualização de 08/11/2026:** as comparações, contagens e tabelas agora usam
um conjunto por usina e mês do ano, após validar a igualdade exata de todos os
parâmetros entre todos os anos, em cada fonte. Divergências entre anos bloqueiam
a geração, com identificação dos valores; não há média, arredondamento ou escolha
silenciosa de um ano. Todas as grandezas e tolerâncias permanecem. Veja o
[plano implementado e as verificações](PLANO_COMPARACAO_MENSAL_SEM_REPETICAO_ANUAL.md).
O intervalo de mês/ano seleciona meses com ocorrência no intervalo e conta cada
conjunto uma única vez. Os totais brutos do horizonte permanecem identificados
na tabela de fontes, separados dos conjuntos comparados. Gere um novo HTML para
usar essa regra; os relatórios antigos permanecem com a regra da sua geração.

Os relatórios gerados ficam em `relatorios/` e podem ser consultados no navegador
sem executar o gerador novamente. O repositório contém o programa e a documentação;
os relatórios e os insumos de cada estudo são locais e não acompanham a cópia do Git.

## Como executar

1. Abra `EXECUTAR_COMPARADOR.bat` na raiz desta pasta.
2. Selecione/confira o parquet do novo modelo, o parquet enriquecido NEWAVE e a pasta do deck do novo modelo.
3. Clique em **Gerar relatório HTML**; a janela informa a tolerância fixa das médias e desvios.
4. O resultado é salvo na pasta `relatorios` e aberto no navegador.

A primeira execução prepara as bibliotecas ausentes na pasta local `.python_packages`. É necessário Python 3.10 ou mais recente; a conexão com a internet só é necessária se faltar alguma biblioteca. O programa não depende da instalação ou dos módulos do avaliador anterior.

## Consulta

**Indicadores por aba, 09/11/2026:** Coeficientes mensais tem 12 cartões,
Visão geral tem 11 e as demais abas têm 8. Os três cartões de combinações
usina–mês aparecem somente em Visão geral e Coeficientes mensais.
O contador de `sc` aparece somente em Coeficientes mensais.
Todas mostram estatísticas
do recorte. Nas sete abas de detalhe, os cartões usam todas as linhas após
os filtros gerais, Resultado e cabeçalhos, antes da paginação. Combinações e
usinas reprovadas são contadas uma vez; parâmetros/coeficientes são contados
individualmente. Reprovados = fora da tolerância + `sc`; as taxas usam todos os
avaliados (dentro + fora + `sc`). Um grupo com `sc` é reprovado, inclusive quando
não há comparação numérica possível. Veja [Indicadores por aba](INDICADORES_POR_ABA.md).

**Atualização de 09/11/2026:** todas as colunas das sete tabelas de detalhe têm
filtros de cabeçalho pelo botão **▾**. Há busca e multisseleção de valores,
condições de texto e filtros numéricos, combináveis e independentes por aba.
Consulte [Filtros de cabeçalho](FILTROS_CABECALHO.md). Gere um novo HTML para
incorporar os controles; os arquivos HTML já gerados são independentes do programa.

As abas são Visão geral, Ordem PARP, Coeficientes mensais, Coeficiente anual, Médias mensais, Médias anuais, Desvio padrão mensal e Desvio padrão anual. A visão inicial contém todas as usinas. Busque uma usina por nome ou ID e escolha o intervalo de mês/ano; esses controles valem para todas as abas. Clique em qualquer título de coluna para classificar as linhas. Há paginação e seleção do resultado nas tabelas de detalhe.

Quando uma tabela ultrapassa a largura disponível, há barras de rolagem horizontal acima e abaixo dela, sincronizadas. A barra superior se adapta à largura da janela e às mudanças de página e de filtros.

A diferença apresentada é absoluta. “Dentro da tolerância” significa diferença
menor ou igual à tolerância. Com ordens diferentes, todos os lags AR mensais
ativos em pelo menos um modelo ficam `sc`, inclusive os comuns, mantendo seus
valores e sem diferença/tolerância. Lags inativos nos dois não geram comparações.
A ordem ajustada é comparada exatamente. Anual, médias e desvios mantêm suas
comparações. Os limites estão registrados nos dados e nas colunas das tabelas.

Coeficientes mensais e anual usam a unidade inteira impressa de cada valor NEWAVE:
`0,001 × 10^e`. Não se usa a maior tolerância de outra usina, mês ou lag.
Médias e desvios das componentes mensal e anual usam **0,01 m³/s fixo**,
independentemente da magnitude ou sinal da referência. Diferença igual ao limite
é aprovada. Nenhum valor de origem ou diferença é arredondado para a classificação.

A coluna Tolerância mostra o limite absoluto efetivamente aplicado em cada linha.
Gere um novo HTML pelo `.bat` para aplicar a regra; relatórios anteriores preservam
o critério registrado na geração original.

Busca e filtros não removem os dados do HTML. O arquivo contém o resultado de todas as usinas e datas, e pode ser compartilhado como um único arquivo. Nenhum recurso externo é carregado pela página. O arquivo também contém os caminhos das fontes para rastreabilidade.

## Linha de comando

Execute a partir da raiz do comparador:

```powershell
python -m comparador.executar --novo "CAMINHO_PARQUET_NOVO" --newave "CAMINHO_PARQUET_NEWAVE" --deck "PASTA_DECK_NOVO" --saida "relatorios/comparacao.html" --sem-abrir
```

Opcionalmente, `--deck-newave "PASTA_DECK_NEWAVE"` confere também o horizonte do `dger.dat`. O formato atual do parquet NEWAVE já fornece seus próprios nomes e datas.

Se faltar uma correspondência de usina e mês/ano, ou se um parâmetro estiver inconsistente, a comparação inteira é interrompida com uma explicação. As fontes são somente lidas; um relatório anterior é preservado se uma nova geração falhar.

## Verificações

```powershell
python -m testes
```

As regras completas estão em `documentacao/PLANO_COMPARADOR_PARAMETROS.md`.
