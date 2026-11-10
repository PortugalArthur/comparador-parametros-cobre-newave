# Comparador de parâmetros — COBRE × NEWAVE

Programa em Python que compara os parâmetros ajustados do novo modelo (COBRE)
com o NEWAVE **ou com outra versão do novo modelo** e gera um **único relatório HTML interativo**, com
tabelas de todas as usinas e datas. O relatório funciona offline no navegador.

## O que é comparado

- Ordem ajustada do modelo PARP.
- Coeficientes autorregressivos mensais, por lag.
- Coeficiente da componente anual.
- Médias e desvios padrão mensais e da componente anual.

As correspondências usam o **nome da usina e o mês/ano**; os IDs dos modelos
podem ser diferentes. Os valores são lidos dos Parquets enriquecidos, preservando
os parâmetros dos ajustes originais.

Antes da comparação, o programa confere todos os cenários e exige que cada
parâmetro da mesma usina e mês do ano seja exatamente igual entre todos os anos.
Qualquer diferença entre anos bloqueia a geração, identificando os valores reais.
Após a validação, compara e conta **um conjunto por usina e mês do ano**:
12 conjuntos quando os 12 meses estão presentes, mantendo todas as grandezas
e as regras de lags ativos e `sc`. Não calcula médias entre anos nem preenche
meses ausentes. [Especificação e verificações](documentacao/PLANO_COMPARACAO_MENSAL_SEM_REPETICAO_ANUAL.md).

As tabelas exibem Janeiro a Dezembro. O intervalo de mês/ano continua disponível:
um conjunto aparece se houver pelo menos uma ocorrência daquele mês no intervalo,
sempre contado uma única vez. A validação abrange todos os anos antes dos filtros.
Relatórios antigos preservam seus dados incorporados; gere um novo HTML pelo `.bat`
para usar a consolidação mensal.

Nas sete abas de detalhe, cada cabeçalho tem um botão **▾** para filtrar a
coluna, como no Excel. É possível selecionar vários valores, buscar opções,
combinar colunas e aplicar condições de texto ou limites numéricos. Os filtros
ficam guardados por aba durante a consulta e abrangem todas as páginas.
Use **Limpar coluna**, **Limpar filtros desta tabela** ou **Limpar filtros**
para remover um filtro, os filtros da aba ou todos os filtros, respectivamente.
Esses filtros locais alteram apenas a tabela de detalhe; a Visão geral mantém
o recorte dos filtros gerais. [Uso e verificações](documentacao/FILTROS_CABECALHO.md).

Cada aba também tem cartões de indicadores com combinações e usinas aprovadas
e reprovadas, taxas de aprovação/reprovação e contagens de avaliados. Nas abas de detalhe, os
cartões respondem a todos os filtros ativos, incluindo cabeçalhos e Resultado,
antes da paginação. **Reprovados = fora da tolerância + sc**; a taxa é
`reprovados / (dentro + fora + sc) × 100`. O contador separado de `sc` aparece
somente na aba Coeficientes mensais e já está incluído nos reprovados.
Sem linhas avaliadas, ambas as taxas aparecem **—**; um recorte somente `sc`
tem 100% de reprovação. Grupos aprovados não têm reprovações nem `sc` no recorte.
[Definições e verificações](documentacao/INDICADORES_POR_ABA.md).

O HTML contém oito abas: Visão geral, Ordem PARP, Coeficientes mensais,
Coeficiente anual, Médias mensais, Médias anuais, Desvio padrão mensal e Desvio padrão anual. As tabelas oferecem busca, filtros,
ordenação, paginação e rolagem horizontal acima e abaixo do conteúdo.

## Requisitos

- Python 3.10 ou superior, com `pip`; execução verificada com Python 3.12.
- Windows e `Tkinter` para a janela e o atalho `.bat`.
- Internet caso seja necessário instalar bibliotecas na primeira execução.

O programa verifica e instala automaticamente as bibliotecas ausentes na pasta
local `.python_packages/`. Também é possível instalá-las manualmente:

```powershell
python -m pip install -r requirements.txt
```

Para consultar o HTML já gerado, é necessário somente um navegador.

## Como executar

1. Baixe ou clone este repositório.
2. Abra **EXECUTAR_COMPARADOR.bat**.
3. Escolha **Novo modelo × NEWAVE** ou **Novo modelo × Novo modelo**.
4. Selecione os dois Parquets enriquecidos e o deck da fonte A. Na comparação
   entre versões, selecione também o deck da fonte B; cada deck deve conter
   `system/hydros.json` e `stages.json`. Informe os nomes/versões das fontes.
5. Clique em **Gerar relatório HTML**. Médias e desvios usam tolerância fixa de 0,01 m³/s.

O relatório é gravado em `relatorios/` e aberto no navegador. As entradas são
somente lidas. Insumos, configurações pessoais, bibliotecas instaladas e
relatórios gerados são ignorados pelo Git.

## Regras de comparação

A diferença é absoluta: `|novo modelo − NEWAVE|`. A ordem ajustada é comparada
exatamente. Para cada coeficiente mensal e anual, a tolerância é
`0,001 × 10^e`, com `e` do formato impresso NEWAVE `0.XXXE±YY`, individualmente
por usina, mês e coeficiente. Por exemplo, `0.393E+00` usa 0,001 e `0.393E-01`
usa 0,0001. Zero ativo usa `e=0`; referência ausente não recebe tolerância.
Os coeficientes AR mensais só são comparados quando as ordens são iguais.
Com ordens diferentes, todos os lags ativos em pelo menos um modelo ficam
`sc`, inclusive os comuns: os valores são preservados e diferença/tolerância
ficam ausentes. Lags inativos nos dois não entram nas contagens. O coeficiente
anual e as médias/desvios mantêm suas comparações independentes da ordem.

Para médias e desvios padrão mensais e anuais, a tolerância absoluta é
**0,01 m³/s fixa**, inclusive para referência zero. Não há campo ou argumento
de percentual. A diferença igual à tolerância é classificada dentro do limite.

Na comparação de duas versões, médias e desvios também usam 0,01 m³/s.
A regra de precisão dos coeficientes mantém o limite global por tipo e usa
os `float64` nativos das duas fontes, sem atribuir a nenhuma delas a precisão
de impressão do NEWAVE. Por isso, o limite pode ser muito menor que 0,01.
Detalhes e verificações em [Comparação entre versões](documentacao/COMPARACAO_ENTRE_VERSOES.md).

## Linha de comando

```powershell
python -m comparador.executar --novo "C:\dados\novo.parquet" --newave "C:\dados\newave.parquet" --deck "C:\dados\deck_cobre" --saida "relatorios\comparacao.html" --sem-abrir
```

Relatórios anteriores preservam suas regras; gere um novo HTML para aplicar os limites atuais.
`--deck-newave` é opcional e permite conferir o horizonte também no `dger.dat`.

Para comparar duas versões, acrescente `--tipo-comparacao novo_novo`,
`--deck-referencia "C:\dados\deck_b"`, `--rotulo-novo "COBRE 0.19.1"` e
`--rotulo-referencia "COBRE 0.20.0"`. Por compatibilidade, `--newave` continua
sendo o nome do argumento do segundo Parquet; nesse modo ele recebe o arquivo COBRE B.

## Testes e documentação

```powershell
python -m testes
```

Os testes usam dados pequenos em diretórios temporários e não precisam dos
Parquets reais do estudo.

- [Instruções completas](documentacao/README.md)
- [Especificação e regras do comparador](documentacao/PLANO_COMPARADOR_PARAMETROS.md)

As pastas `comparador/`, `infraestrutura/` e `recursos/` contêm a implementação.
`testes/` contém as verificações automatizadas e utilitários de auditoria.
