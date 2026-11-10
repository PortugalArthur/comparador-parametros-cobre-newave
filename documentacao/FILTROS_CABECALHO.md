# Filtros de cabeçalho das tabelas de detalhe

Implementado em 09/11/2026 nos recursos do HTML do comparador.

## Uso

Nas abas Ordem PARP, Coeficientes mensais, Coeficiente anual, Médias mensais,
Médias anuais, Desvio padrão mensal e Desvio padrão anual, o botão **▾** ao lado do título abre o filtro daquela coluna. Todas as
colunas são filtráveis: usina, mês, lag, parâmetro, valores das fontes, diferença,
tolerância, resultado, unidade, motivo de `sc` e ordens, conforme a tabela.

- Selecione um ou mais valores e clique em **Aplicar**.
- A busca localiza opções da lista. **Somente resultados da busca** seleciona
  apenas os valores encontrados; **Desmarcar todos** permite escolher do zero.
- A caixa **Selecionar todos os resultados da busca** marca ou desmarca todas
  as opções encontradas, incluindo as que ainda não foram exibidas na lista.
- Listas longas mostram 100 opções inicialmente, com **Mostrar mais**; a busca
  sempre consulta a lista completa, não só as primeiras 100 opções.
- Nas colunas numéricas, use igual, diferente, maior, maior ou igual, menor,
  menor ou igual e entre, com limites inclusivos. São aceitos vírgula ou ponto
  decimal, sinais e notação científica, por exemplo `-0,1` e `1e-3`.
- Nas colunas de texto, use contém, não contém, igual, diferente, começa com
  e termina com. As condições de texto ignoram diferenças de caixa e acentuação.
- Se uma condição e uma seleção de valores estiverem ativas na mesma coluna,
  a linha deve atender às duas. Filtros de várias colunas também se combinam
  por interseção: todas as condições precisam ser atendidas.
- Os botões de cabeçalho ficam azuis quando o filtro está ativo. A barra da
  tabela informa quantas colunas estão filtradas.
- **Cancelar**, **×**, Escape ou clique fora do menu descartam as mudanças
  ainda não aplicadas.
- **Limpar coluna** remove apenas aquele filtro. **Limpar filtros desta tabela**
  remove os filtros de coluna e o filtro Resultado da aba atual. O botão geral
  **Limpar filtros** remove os filtros gerais e os filtros das sete abas.

## Escopo e precisão

Os filtros locais abrangem todas as linhas do recorte geral, antes da paginação.
A contagem e o número de páginas refletem o resultado combinado. Aplicar ou
limpar um filtro retorna à primeira página. Ordenação e tamanho de página são
preservados. A busca de usina e o intervalo gerais continuam funcionando em
conjunto com os filtros locais.

Os filtros ficam guardados separadamente por aba durante a consulta, inclusive
ao trocar de aba ou alterar o recorte geral. Reabrir ou recarregar o HTML inicia
a consulta sem os filtros locais da sessão anterior.

As opções de valores pertencem ao recorte dos filtros gerais e incluem todas
as páginas. Os demais filtros locais não retiram opções dessa lista. Uma seleção
mantida que não pertença ao novo recorte continua disponível para revisão.

Valores ausentes aparecem como **— (sem valor)** e textos vazios como
**(Texto vazio)**. Nenhum deles é transformado em zero. Condições numéricas
operam somente sobre números; valores ausentes podem ser escolhidos pela lista.

Os filtros comparam os valores numéricos completos incorporados ao HTML. As
opções da lista preservam a representação completa do número, distinguindo
valores próximos. A formatação da célula e as tolerâncias de comparação entre
modelos não são usadas para aproximar valores de filtros. Entradas numéricas
inválidas e limites invertidos não podem ser aplicados.

Os filtros são exclusivamente de exibição. Não modificam parâmetros, diferenças,
tolerâncias, classificações ou os dados incorporados. A Visão geral continua
seguindo apenas os filtros gerais de usina e intervalo. Os 12 conjuntos mensais
e todas as validações de cenários e anos permanecem inalterados.

## Verificações

- 41 testes Python existentes aprovados; nenhum módulo de cálculo alterado.
- Auditor de navegador `testes/auditar_filtros_cabecalho.cjs`: todas as 60 colunas
  das sete abas nos dois modos, multisseleção, interseção de colunas, oito casos
  numéricos, seis condições de texto, ausência de valores e `sc` onde presentes,
  entradas inválidas, listas com mais de 100 opções, cancelamento, estado por aba,
  paginação e interação com o recorte geral. Os dados incorporados são conferidos
  antes e depois dos filtros.
- Auditores existentes de tabelas e de navegador preservam a conferência das
  oito abas, contagens, ordenação, unidade, filtros gerais e rolagem.
- Comparação dos novos relatórios com as referências anteriores: 1908 conjuntos
  em cada modo, com valores, diferenças, limites e classificações idênticos.

Relatórios: `relatorios/comparacao_mensal_novo_newave_filtros.html` e
`relatorios/comparacao_mensal_novo_novo_filtros.html`. Evidências e capturas em
`outputs/verificacao/filtros_cabecalho/`. Os HTMLs anteriores e os insumos foram
preservados. As próximas gerações pelo `.bat` já incluem os novos controles.
