# Comparador de parâmetros — COBRE × NEWAVE

Programa em Python que compara os parâmetros ajustados do novo modelo (COBRE)
com os parâmetros do NEWAVE e gera um **único relatório HTML interativo**, com
tabelas de todas as usinas e datas. O relatório funciona offline no navegador.

## O que é comparado

- Ordem ajustada do modelo PARP.
- Coeficientes autorregressivos mensais, por lag.
- Coeficiente da componente anual.
- Médias e desvios padrão mensais e da componente anual.

As correspondências usam o **nome da usina e o mês/ano**; os IDs dos modelos
podem ser diferentes. Os valores são lidos dos Parquets enriquecidos, preservando
os parâmetros dos ajustes originais.

O HTML contém cinco abas: Visão geral, Ordem PARP, Coeficientes mensais,
Coeficiente anual e Médias e desvios padrão. As tabelas oferecem busca, filtros,
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
3. Selecione o Parquet enriquecido do novo modelo, o Parquet enriquecido do
   NEWAVE e a pasta do deck do novo modelo, contendo `system/hydros.json` e
   `stages.json`.
4. Informe o percentual de tolerância para médias e desvios padrão.
5. Clique em **Gerar relatório HTML**.

O relatório é gravado em `relatorios/` e aberto no navegador. As entradas são
somente lidas. Insumos, configurações pessoais, bibliotecas instaladas e
relatórios gerados são ignorados pelo Git.

## Regras de comparação

A diferença é absoluta: `|novo modelo − NEWAVE|`. A ordem ajustada é comparada
exatamente. Para os coeficientes, a tolerância é global por tipo e corresponde
à precisão do valor menos preciso. Lags comuns são comparados; `sc` indica lag
ativo em apenas um dos modelos.

Para médias e desvios padrão, o usuário escolhe `x` antes de gerar o HTML.
Cada linha usa `x/100 × |NEWAVE|` como tolerância. Se NEWAVE é zero, a tolerância
é zero. A diferença igual à tolerância é classificada dentro do limite.

## Linha de comando

```powershell
python -m comparador.executar --novo "C:\dados\novo.parquet" --newave "C:\dados\newave.parquet" --deck "C:\dados\deck_cobre" --percentual-estatisticas "2,5" --saida "relatorios\comparacao.html" --sem-abrir
```

O percentual acima é um exemplo de execução, não um valor recomendado.
`--deck-newave` é opcional e permite conferir o horizonte também no `dger.dat`.

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
