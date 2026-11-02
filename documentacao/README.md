# Comparador de parâmetros — novo modelo × NEWAVE

Programa independente do avaliador de testes estatísticos. Lê os parâmetros enriquecidos dos dois modelos e produz um único HTML com cinco abas, exclusivamente com tabelas. O HTML funciona localmente, sem internet nem instalação de um servidor.

Os relatórios gerados ficam em `relatorios/` e podem ser consultados no navegador
sem executar o gerador novamente. O repositório contém o programa e a documentação;
os relatórios e os insumos de cada estudo são locais e não acompanham a cópia do Git.

## Como executar

1. Abra `EXECUTAR_COMPARADOR.bat` na raiz desta pasta.
2. Selecione/confira o parquet do novo modelo, o parquet enriquecido NEWAVE e a pasta do deck do novo modelo.
3. No mesmo quadro, preencha **Tolerância para médias e desvios padrão (% do valor NEWAVE)** com o percentual desejado. O campo é obrigatório e aceita vírgula decimal. A primeira execução não sugere um valor; nas próximas, lembra o último percentual que você usou.
4. Clique em **Gerar relatório HTML**.
5. O resultado é salvo na pasta `relatorios` e aberto no navegador.

A primeira execução prepara as bibliotecas ausentes na pasta local `.python_packages`. É necessário Python 3.10 ou mais recente; a conexão com a internet só é necessária se faltar alguma biblioteca. O programa não depende da instalação ou dos módulos do avaliador anterior.

## Consulta

As abas são Visão geral, Ordem PARP, Coeficientes mensais, Coeficiente anual e Médias e desvios padrão. A visão inicial contém todas as usinas. Busque uma usina por nome ou ID e escolha o intervalo de mês/ano; esses controles valem para todas as abas. Clique em qualquer título de coluna para classificar as linhas. Há paginação e seleção do resultado nas tabelas de detalhe.

Quando uma tabela ultrapassa a largura disponível, há barras de rolagem horizontal acima e abaixo dela, sincronizadas. A barra superior se adapta à largura da janela e às mudanças de página e de filtros.

A diferença apresentada é absoluta. “Dentro da tolerância” significa diferença menor ou igual à tolerância. `sc` indica lag ativo em apenas um modelo; os lags comuns continuam sendo comparados. Lags inativos nos dois não geram comparações. A ordem ajustada é comparada exatamente. As regras de tolerância estão descritas na Visão geral.

Para os coeficientes mensais e o coeficiente anual, a tolerância continua global por tipo e corresponde à unidade inteira do valor menos preciso (0,01 nos insumos atuais). Para cada média e desvio padrão, a tolerância agora é **x/100 × |valor NEWAVE|**, calculada individualmente por usina e estágio. O mesmo percentual x se aplica aos quatro campos (médias e desvios da componente anual e mensais), mas o limite absoluto muda conforme a referência de cada linha. Se NEWAVE for zero, a tolerância é zero. x = 0 exige igualdade exata; não há um limite mínimo adicional de arredondamento.

O percentual escolhido aparece no HTML e a coluna Tolerância mostra o limite absoluto de cada linha, em m³/s. Para aplicar esta nova regra, gere um novo HTML pelo `.bat`; relatórios anteriores preservam o critério registrado na geração original.

Busca e filtros não removem os dados do HTML. O arquivo contém o resultado de todas as usinas e datas, e pode ser compartilhado como um único arquivo. Nenhum recurso externo é carregado pela página. O arquivo também contém os caminhos das fontes para rastreabilidade.

## Linha de comando

Execute a partir da raiz do comparador:

```powershell
python -m comparador.executar --novo "CAMINHO_PARQUET_NOVO" --newave "CAMINHO_PARQUET_NEWAVE" --deck "PASTA_DECK_NOVO" --percentual-estatisticas "SEU_PERCENTUAL" --saida "relatorios/comparacao.html" --sem-abrir
```

Opcionalmente, `--deck-newave "PASTA_DECK_NEWAVE"` confere também o horizonte do `dger.dat`. O formato atual do parquet NEWAVE já fornece seus próprios nomes e datas.

Se faltar uma correspondência de usina e mês/ano, ou se um parâmetro estiver inconsistente, a comparação inteira é interrompida com uma explicação. As fontes são somente lidas; um relatório anterior é preservado se uma nova geração falhar.

## Verificações

```powershell
python -m testes
```

As regras completas estão em `documentacao/PLANO_COMPARADOR_PARAMETROS.md`.
