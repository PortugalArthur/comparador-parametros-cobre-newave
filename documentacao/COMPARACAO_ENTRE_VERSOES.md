# Comparação entre versões do novo modelo

Implementação local em 06/11/2026, em `C:\Users\Pichau\Desktop\ONS\Vazoes\COMPARADOR_PARAMETROS_COBRE_NEWAVE`.

**Atualização de 08/11/2026:** os dois modos também consolidam as repetições entre
anos, após validar igualdade exata de todos os campos. As comparações, contagens
e tabelas usam usina/mês do ano; o pareamento do horizonte completo permanece.
Veja o [plano implementado](PLANO_COMPARACAO_MENSAL_SEM_REPETICAO_ANUAL.md).
Os registros abaixo sobre integridade do arquivo `regras.py` e 33 testes se referem
à implementação de 06/11; a atualização mensal altera a organização das linhas,
preserva as funções numéricas e foi verificada com 41 testes.

**Atualização de 09/11/2026:** médias e desvios usam **0,01 m³/s fixo** nos dois
modos. O campo e o argumento CLI de percentual foram removidos. No modo novo ×
novo, a precisão dos coeficientes continua baseada nos float64 das fontes.
As afirmações de preservação integral das contas abaixo documentam a alteração
original de 06/11; esta atualização substitui a antiga regra percentual.

## Seleção e entradas

O `.bat` existente abre a janela com a escolha entre **Novo modelo × NEWAVE** e **Novo modelo × Novo modelo**. A primeira fonte é A; a segunda é B. Cada fonte pode receber um nome, por exemplo `COBRE 0.19.1` e `COBRE 0.20.0`.

No segundo modo, selecionar dois Parquets COBRE enriquecidos e os respectivos decks A e B. É permitido selecionar o mesmo deck para ambos quando ele realmente corresponde aos dois estudos. Os Parquets devem ser arquivos distintos. O programa não altera seus metadados para fingir que a fonte B é NEWAVE.

Cada arquivo é associado ao seu cadastro/calendário e, depois, os modelos são pareados pelo nome normalizado da usina e pelo mesmo mês/ano. IDs diferentes continuam permitidos. As mesmas validações de parâmetros, ordens, lags e constância entre cenários continuam em vigor. Arquivos incompatíveis interrompem a geração.

## Contas preservadas

**`comparador/regras.py` não foi alterado.** Continuam exatamente as mesmas funções para diferença absoluta, tolerâncias, limite inclusivo e classificação de lags comuns/`sc`.

- Ordem: igualdade exata.
- Médias/desvios: tolerância absoluta fixa de **0,01 m³/s**, inclusive para referência zero.
- Coeficientes: maior unidade de precisão observada por tipo, considerando a origem real das fontes.

A última regra já reconhecia `float64` nativo do COBRE. Para dois COBRE, aplica-se essa resolução a ambos; **não se aplica a precisão decimal impressa do PARPVAZ**. Portanto, o limite pode ser da ordem da resolução numérica do `float64`, muito menor que 0,01. Isso é a mesma regra aplicada a entradas de outra origem, não um arredondamento ou novo ajuste para aproximar resultados.

O processamento chama `comparar` diretamente. Depois, acrescenta identificação das versões e atualiza apenas as descrições da referência. Não recalcula parâmetros, diferenças ou classificações para adequar o resultado ao visual.

## Interface e compatibilidade

As oito abas e suas tabelas permanecem. Títulos, colunas de valores/ordens, motivos de `sc`, fontes e descrições usam os nomes escolhidos. A coluna Unidade continua à direita de Resultado e as ordens continuam no fim da tabela mensal. O HTML mantém filtros, ordenação, paginação e consulta offline.

CLI mantém os argumentos antigos. Novo exemplo:

```powershell
python -m comparador.executar --tipo-comparacao novo_novo --novo "C:\dados\versao_a.parquet" --newave "C:\dados\versao_b.parquet" --deck "C:\dados\deck_a" --deck-referencia "C:\dados\deck_b" --rotulo-novo "COBRE 0.19.1" --rotulo-referencia "COBRE 0.20.0" --sem-abrir
```

A designação `--newave` identifica o segundo argumento por compatibilidade, não a origem do arquivo no modo `novo_novo`.

## Verificações

- 33 testes automatizados: os 28 anteriores e cinco casos novos.
- Resultados, tolerâncias e classificações Novo modelo × NEWAVE comparados com uma referência salva **antes** das alterações: idênticos.
- Hash de `comparador/regras.py` preservado.
- Dois Parquets com os mesmos valores e IDs diferentes: diferenças zero, sem divergências inventadas.
- Lags comuns, ordens diferentes e `sc` conferidos no novo modo.
- Coeficiente realmente diferente continua diferente, sem receber a tolerância artificial do NEWAVE.
- Novo modo conferido diretamente contra a saída da função de comparação já existente.
- Bloqueios de origem, deck, calendário e nomes ambíguos conferidos.
- Tabelas JavaScript auditadas nos dois modos, incluindo valores, limites, resumos, ordenação e posicionamento das colunas.
- Os dois HTMLs abertos em Chrome offline: cinco abas, nomes corretos, busca e nenhuma exceção ou requisição externa.
- Janela conferida com seleção de modo, ativação do deck B e encaminhamento dos argumentos; teste isolado não escreveu nas preferências pessoais.

Evidências locais em `outputs/verificacao/duas_versoes/`. Os dados pequenos usados nos testes são artificiais e explicitamente isolados; os insumos reais não foram modificados. Esta mudança local não publica automaticamente uma nova versão no GitHub.
