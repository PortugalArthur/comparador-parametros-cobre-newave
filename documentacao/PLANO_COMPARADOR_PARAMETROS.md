# Comparador de parâmetros — novo modelo × NEWAVE

Implementado em 30/10/2026, na pasta independente `COMPARADOR_PARAMETROS_COBRE_NEWAVE`.

**Atualização de 08/11/2026:** o pareamento continua validando o horizonte completo,
mas as comparações e contagens agora usam usina/mês do ano, após exigir igualdade
exata entre os anos em cada fonte. O [plano de consolidação mensal](PLANO_COMPARACAO_MENSAL_SEM_REPETICAO_ANUAL.md)
prevalece sobre as descrições anteriores de linhas e totais por usina/estágio.
Todas as grandezas e as regras numéricas permanecem.

## Objetivo e separação

Criar um programa independente do avaliador estatístico, em uma pasta própria na Área de Trabalho, com um `.bat` de execução. Não alterar o avaliador existente, os geradores nem os parquets de origem.

Calcular antecipadamente as comparações de todas as usinas e estágios e disponibilizá-las em um único HTML com CSS e JavaScript incorporados, que funcione sem internet e sem um servidor. O HTML de balanços fornecido pelo usuário serve como inspiração de organização, cores, abas e tabelas; seus dados e seu código executável não serão incorporados.

## Entradas e correspondência

1. Parquet enriquecido do novo modelo (COBRE).
2. Parquet enriquecido do NEWAVE.
3. Pasta do deck do novo modelo, com `system/hydros.json` e `stages.json`.
4. Deck NEWAVE somente quando necessário. O formato atual do parquet NEWAVE já contém cadastro e calendário próprios; a linha de comando permitirá também conferir o horizonte com o `dger.dat`.

Associar usinas por nome normalizado e único, conferindo os respectivos identificadores. Nunca presumir que os IDs dos dois modelos são iguais. Associar estágios pelo mesmo mês **e ano**, com limites mensais válidos. Não comparar apenas por `stage_id`, nem pelo mês do ano isoladamente. O horizonte e o número de usinas serão identificados nos dados.

## Campos comparados

- Ordem ajustada: `ar_order`.
- Coeficientes mensais: `ar_coefficient_lag_1` até o maior lag disponível, sem fixar seis como limite do programa.
- Coeficiente anual: `annual_coefficient`.
- Média e desvio da componente anual: `annual_mean_m3s`, `annual_std_m3s`.
- Média e desvio mensal: `seasonal_mean_m3s`, `seasonal_std_m3s`.

Para os parquets atuais são 12 campos, incluindo os seis coeficientes mensais. Comparar os parâmetros armazenados, sem recalcular médias, desvios ou ajustes a partir das vazões sintéticas. Conferir todas as linhas para assegurar que o parâmetro é constante entre os cenários de uma mesma usina e estágio; só então consolidar uma linha por par.

## Diferença e tolerância

Regra atualizada em 09/11/2026, por determinação do usuário. Exibir a diferença
absoluta `abs(novo_modelo - NEWAVE)`, preservando os valores originais.

A ordem é inteira e sua comparação é exata. Para cada coeficiente mensal e anual,
usar **0,001 × 10^e**, com `e` do formato NEWAVE `0.XXXE±YY`. A tolerância é
individual por usina, mês e coeficiente; não utilizar a maior unidade de outro
valor. Exemplos: `0.393E+00` usa 0,001; `0.393E-01` usa 0,0001;
`0.105E+01` usa 0,01. Para zero ativo, o perfil `0.000E+00` implica 0,001.
Coeficiente ausente no NEWAVE não recebe tolerância nem valor substituto.

O esquema NEWAVE enriquecido versão 2 preserva os coeficientes provenientes de
três algarismos significativos. O Parquet não conserva zeros finais nem a notação
original; não contar casas decimais do float. Para valor não nulo, reconstruir
a unidade como `10 ** (Decimal(str(abs(valor))).adjusted() - 2)`.
Um perfil não reconhecido deve bloquear a comparação.

Para médias e desvios mensais e anuais, usar **0,01 m³/s fixo**, inclusive para
referência zero, sem percentual nem dependência da magnitude ou sinal. Remover
o campo percentual da janela e o argumento CLI `--percentual-estatisticas`.
Preferências antigas de percentual não afetam o cálculo. Os dois modos aplicam
o mesmo limite fixo às quatro grandezas.

Na comparação novo × novo, os coeficientes continuam usando o limite global por
tipo da resolução float64 das duas fontes; não atribuir precisão NEWAVE a uma
fonte COBRE. Médias e desvios usam 0,01 m³/s também nesse modo.

Gravar o limite efetivo de cada comparação no resultado e na coluna Tolerância.
A Visão geral deve identificar as fórmulas, unidades e referência de impressão.
Diferença igual ao limite é aprovada: comparar com `Decimal(str(...))` antes da
geração, sem arredondar os valores para mascarar divergências. Filtros não
recalculam limites. Relatórios anteriores preservam o critério de sua geração.

## Ordens diferentes e `sc`

Regra de 09/11/2026: os coeficientes AR mensais só são comparados quando as
ordens ajustadas da mesma usina/mês forem iguais. Com ordens diferentes,
todos os lags ativos em pelo menos uma fonte recebem `sc`, inclusive os comuns
e mesmo quando seus valores forem iguais ou zero. Preservar os coeficientes
de cada fonte nas respectivas colunas; diferença e tolerância ficam `None`.
O motivo deve informar as duas ordens. Não calcular a diferença ou o limite
nesses casos, nem reutilizar uma tolerância global no HTML.

Lags inativos nos dois modelos não geram linhas nem contagens. Os `sc` ativos
continuam incluídos nos reprovados e nas taxas, sem dupla contagem. A ordem é
comparada exatamente e reprova quando diferente. O coeficiente anual, médias
e desvios mantêm suas próprias comparações. A regra vale nos dois modos.

## Erros de consistência

Bloquear a comparação inteira e informar o problema quando houver usina/mês/ano sem correspondente, grade mensal incompleta, identificação ambígua, calendário incompatível, parâmetro ativo ausente ou não finito, ordem inválida, desvio negativo ou variação do parâmetro entre cenários. Uma ausência inesperada não pode virar `sc`. Lags inativos devem ser nulos. Preservar um relatório anterior se uma nova execução falhar.

## Apresentação combinada com o usuário

**Somente tabelas. Não haverá gráficos nem mapas de calor.** A visão inicial abrange todas as usinas; não se exige selecionar uma usina para analisar o resultado.

Cinco abas:

1. **Visão geral**: resumo por tipo, por usina e por mês/ano, incluindo quantidade comparável, dentro e fora da tolerância e `sc`; tabela das tolerâncias utilizadas e identificação das fontes.
2. **Ordem PARP**: valores de ambos os modelos, diferença absoluta, tolerância zero e resultado.
3. **Coeficientes mensais**: mesmos elementos, discriminados por lag e com as ordens de ambos os modelos para explicar `sc`. “Ordem novo modelo” e “Ordem NEWAVE” são as duas últimas colunas, à direita da tabela, conforme correção do usuário.
4. **Coeficiente anual**: comparação dos coeficientes anuais armazenados.
5. **Médias e desvios padrão**: identificação do parâmetro, valores dos dois modelos, diferença, unidade, tolerância e resultado.

Busca opcional de usina por nome/ID e intervalo de datas controlam todas as abas. Identificar as combinações nas tabelas pelo nome da usina e mês/ano, sem colunas de ID da usina ou de estágio de qualquer modelo. Os identificadores permanecem somente nos dados internos e nas verificações de correspondência. Permitir mudar a classificação clicando nos títulos das colunas, inclusive valores numéricos, e oferecer paginação para evitar milhares de elementos simultâneos. As tabelas de detalhe terão também seleção de resultado. Filtros não recalculam tolerâncias nem eliminam dados do arquivo HTML.

Usar vírgula decimal e nenhum separador de milhar. Distinguir “Dentro da tolerância”, “Fora da tolerância” e `sc` por texto e cor. Não confundir concordância de parâmetros com aprovação em teste estatístico. Proteger a incorporação de nomes e caminhos no HTML; não utilizar recursos externos.

Em todas as tabelas de comparação, a coluna “Unidade” fica imediatamente à direita de “Resultado”.

Tabelas que ultrapassam a largura disponível devem ter barras de rolagem horizontal tanto acima do cabeçalho quanto na parte inferior, sincronizadas nos dois sentidos e ajustadas automaticamente após paginação, classificação, filtros e mudança da largura da janela.

## Execução e organização

- `EXECUTAR_COMPARADOR.bat`: abre seleção de entradas e gera o HTML.
- `comparador/`: leitura, validação, comparação, relatório e execução.
- `recursos/`: modelo HTML, CSS e navegação/ordenação das tabelas.
- `documentacao/`: este plano e instruções.
- `testes/`: verificações automatizadas.
- `infraestrutura/`: preparação das dependências locais.
- `relatorios/`: resultados gerados, mantendo o histórico por data/hora.

Permitir também execução por linha de comando para reproduzir uma comparação e fazer verificações automatizadas. Publicar o arquivo de saída de forma atômica, apenas depois de concluídas as validações e a geração.

## Verificação

Testar pareamento com IDs distintos, virada de ano e início fora de janeiro; bloqueio de dados incompletos/inconsistentes; lags comuns e `sc`; zeros ativos; tolerância global e limite inclusivo; busca, ordenação numérica, paginação e filtros compartilhados; abertura do HTML sem acesso à rede. Gerar também um relatório com os parquets reais, verificar seu conteúdo e registrar os totais.

### Verificação realizada

- 21 testes automatizados passaram, cobrindo as regras de consistência, pareamento, diferenças/tolerâncias, lags, independência do HTML e preservação da saída anterior em caso de falha.
- Executado com os parquets reais e os decks atuais do novo modelo e do NEWAVE: 159 usinas, 72 meses (01/2026–12/2031), 11448 pares usina–mês; todas as 22896000 linhas de cada parquet foram conferidas antes da consolidação.
- Resultado inicial, antes dos ajustes de tolerância: 87630 comparações de parâmetros, sendo 33696 dentro e 53934 fora da tolerância; 2742 lags ativos em somente um modelo classificados como `sc`. Inicialmente a ordem tinha tolerância zero e todos os demais tipos tinham 0,005. A revisão seguinte passou os coeficientes para 0,01 e ainda manteve médias/desvios em 0,005. A regra vigente de 09/11/2026 para médias/desvios é 0,01 m³/s fixo, definida na seção acima; os números deste item são históricos.
- Conferidos no navegador: cinco abas sem gráficos, ordenação numérica nos dois sentidos, paginação, busca por nome e ID, busca vazia, filtro compartilhado por mês/ano, limpeza dos filtros e motivos de `sc`. Não houve erros ou avisos no console do navegador.
- `.bat` conferido com a opção de ajuda da linha de comando.
- Relatório inicial: `relatorios/comparacao_parametros_atual.html`, aproximadamente 4,6 MB. Evidências: `outputs/verificacao/resultado.json` e `outputs/verificacao/visao_geral.png`.

### Histórico: ajuste da tolerância dos coeficientes — 30/10/2026

- Coeficientes mensais e anual passaram da incerteza de meia unidade para uma unidade inteira de precisão do valor menos preciso: 0,01 nos insumos atuais. Médias e desvios mantêm 0,005; ordem permanece exata.
- 23 testes automatizados passaram, incluindo diferenças entre meia e uma unidade e o limite inclusivo da nova tolerância.
- Os três HTMLs existentes foram reavaliados com os parâmetros incorporados, preservando valores, diferenças, datas e resultados dos demais tipos. Cada relatório passou a ter 38208 comparações dentro e 49422 fora da tolerância, além dos mesmos 2742 `sc`, em 87630 comparações válidas.
- Detalhes da atualização em `outputs/verificacao/atualizacao_tolerancias_coeficientes.json`.

### Percentual de médias/desvios escolhido na janela — 30/10/2026

Campo obrigatório acrescentado ao quadro de seleção das entradas, sem percentual arbitrado pelo programa. O cálculo agora grava o limite absoluto de cada campo por usina e estágio. O HTML registra e mostra o percentual utilizado, incluindo a regra de referência zero. A versão interna dos dados passa a 3; limites globais de médias/desvios são nulos, e os limites válidos ficam incorporados em cada linha.

28 testes passaram, incluindo validação de x, vírgula decimal, referência zero/negativa, limite inclusivo, variação por usina e estágio e preservação das comparações dos coeficientes. Uma execução de verificação com 2,5% e os parquets reais foi salva exclusivamente em `outputs/verificacao/percentual_estatisticas/teste_2_5.html`; esse percentual de teste não foi definido como padrão nem aplicado aos relatórios do usuário.
