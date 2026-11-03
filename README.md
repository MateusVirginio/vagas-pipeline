# 📊 Vagas Pipeline — Mercado de Dados e IA no Brasil

![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)
![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-diário-2088FF?logo=githubactions)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791?logo=postgresql)
![dbt](https://img.shields.io/badge/dbt-1.11-FF694B?logo=dbt)
![Streamlit](https://img.shields.io/badge/Streamlit-online-FF4B4B?logo=streamlit)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)

Pipeline de dados **end-to-end** com arquitetura Medallion que coleta, transforma e visualiza vagas de dados e inteligência artificial no Brasil diariamente.

🔗 **[Dashboard ao vivo](https://vagas-pipeline.streamlit.app)**

---

## 🎯 Problema resolvido

O mercado de dados no Brasil cresce rapidamente, mas é difícil ter uma visão consolidada das vagas abertas, empresas que mais contratam e distribuição por senioridade e região. Este pipeline coleta automaticamente vagas de dados, Machine Learning, Engenharia de IA e MLOps, centralizando tudo em um dashboard interativo atualizado diariamente.

---

## 🏗️ Arquitetura Medallion

```
        ┌────────────────┐
        │    API Gupy    │
        └────────┬───────┘
                 ▼
        ┌────────────────┐
        │ Script Python  │  Agendado com GitHub Actions
        └────────┬───────┘
                 ▼
        ┌────────────────┐
        │  Bronze Layer  │  vagas_raw (PostgreSQL)
        └────────┬───────┘
                 ▼
        ┌────────────────┐
        │  Silver Layer  │  stg_vagas (dbt)
        └────────┬───────┘
                 ▼
        ┌────────────────┐
        │   Gold Layer   │  vagas_por_estado
        │                │  vagas_por_senioridade  (dbt)
        │                │  vagas_por_empresa
        │                │  vagas_por_area
        └────────┬───────┘
                 ▼
        ┌────────────────┐
        │   Streamlit    │  Dashboard publicado online
        └────────────────┘
```

O workflow coleta e grava no Neon, executa `dbt run`, gera embeddings novos ou
alterados e limpa embeddings antigos. As etapas são sequenciais: uma falha
interrompe as etapas posteriores.

O caminho dos embeddings parte de `vagas_raw`:

```text
vagas_raw → preparar texto → validar tokens → comparar hash
                                               ↓ quando necessário
                                    OpenAI Embeddings API
                                               ↓
                                vagas_embeddings (pgvector)
```

A geração incremental está implementada. A consulta por similaridade e sua
integração com um assistente ainda estão em desenvolvimento.

---

## 🛠️ Stack

| Camada | Tecnologia | Função |
|---|---|---|
| Agendamento | GitHub Actions | Execução diária e disparo manual com logs |
| Coleta | Python + Requests | API Gupy |
| Armazenamento | PostgreSQL 15 | Persistência das vagas coletadas |
| Embeddings | OpenAI + tiktoken | Vetores de texto e contagem local de tokens |
| Armazenamento vetorial | pgvector no Neon | Persistência dos embeddings por vaga, variação e modelo |
| Transformação | dbt 1.11 | Camadas Silver e Gold (arquitetura Medallion) |
| Visualização | Streamlit + Plotly | Dashboard interativo publicado online |
| Banco na nuvem | Neon (PostgreSQL serverless) | Banco de produção para o dashboard |
| Infraestrutura | Docker + Compose | Ambiente reproduzível e isolado |
| Gerenciamento | UV | Gerenciamento de dependências Python |

---

## 📁 Estrutura do projeto

```
vagas-pipeline/
├── .github/workflows/
│   └── coleta-diaria.yml        # Agendamento diário e disparo manual
├── src/
│   ├── __init__.py
│   ├── collect.py               # Extract (Gupy) e Load
│   ├── run_dbt.py               # dbt com credenciais de ambiente
│   ├── embedding_text.py        # Normalização, composição, tokens e hash
│   ├── embedding_batches.py     # Lotes por quantidade e tokens
│   ├── gerar_embeddings.py      # Diagnóstico e geração incremental
│   └── limpar_embeddings.py     # Retenção dos embeddings
├── examples/
│   └── gerar_primeiro_embedding.py # Exemplo didático de uma vaga
├── sql/
│   └── 001_criar_vagas_embeddings.sql # Extensão vector e tabela
├── dbt/
│   └── vagas/
│       └── models/
│           ├── staging/
│           │   ├── sources.yml
│           │   └── stg_vagas.sql        # Silver: limpeza e padronização
│           └── marts/
│               ├── vagas_por_estado.sql
│               ├── vagas_por_senioridade.sql
│               ├── vagas_por_empresa.sql
│               └── vagas_por_area.sql
├── streamlit/
│   └── app.py                   # Dashboard interativo
├── docker-compose.yaml
├── .env.example                # Variáveis de ambiente, sem credenciais
├── pyproject.toml
├── uv.lock                     # Versões resolvidas das dependências
└── .gitignore
```

---

## 🚀 Como rodar localmente

### Ambiente local

Instale Python 3.12 e UV. Na raiz do repositório:

```bash
uv sync --locked
```

O `uv.lock` é versionado. `--locked` verifica se ele corresponde ao
`pyproject.toml` e falha se houver divergência, em vez de resolver novas versões.
Ao adicionar uma dependência com `uv add`, versione os dois arquivos.

Crie sua configuração local sem sobrescrever um `.env` existente:

```bash
cp -n .env.example .env
```

Preencha `WAREHOUSE_DATABASE_URL` com a URL do Neon (incluindo
`sslmode=require`) e `OPENAI_API_KEY` para gerar embeddings. O `.env` não deve
ser versionado. `TEST_DATABASE_URL` é opcional e habilita testes de integração.

Para desenvolver em um banco local opcional:

```bash
docker compose up -d postgres
# No .env, use WAREHOUSE_DATABASE_URL=postgresql://vagas:vagas@localhost:5432/vagas?sslmode=disable
```

O Compose usa PostgreSQL 15 com pgvector 0.8.7, mantendo o volume
`vagas-db-volume`. A imagem fornece a extensão, que ainda precisa ser ativada
em cada banco. Depois da primeira coleta, aplique a estrutura dos embeddings:

```bash
docker compose exec -T postgres psql -U vagas -d vagas -v ON_ERROR_STOP=1 \
  < sql/001_criar_vagas_embeddings.sql
```

Para conferir a extensão instalada:

```bash
docker compose exec -T postgres psql -U vagas -d vagas \
  -c "SELECT extversion FROM pg_extension WHERE extname = 'vector';"
```

Execute a coleta, as transformações e o dashboard:

```bash
uv run python src/collect.py
uv run python src/run_dbt.py
uv run streamlit run streamlit/app.py
```

O dashboard lê `DATABASE_URL` de `streamlit/.streamlit/secrets.toml`; configure a
mesma base escolhida para a coleta. O perfil versionado em `dbt/vagas/profiles.yml`
usa `env_var` para `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE` e
`PGSSLMODE`. `run_dbt.py` extrai essas variáveis da URL sem imprimir credenciais
nem gravá-las em arquivos.

### Dev Container / Codespaces

O `.devcontainer/devcontainer.json` usa Python 3.12, instala UV e executa
`uv sync --locked` na criação. O editor seleciona `.venv/bin/python`.
Configure o banco e os Secrets locais conforme descrito acima; o servidor é
iniciado manualmente depois dessa configuração:

```bash
python -m uv run --locked streamlit run streamlit/app.py \
  --server.address 0.0.0.0
```

A porta 8501 é encaminhada pelo Dev Container. O Compose é uma opção separada
para quem tem Docker disponível; dentro de um container, `localhost` identifica
o próprio container. Para Codespaces, a conexão com o Neon pode ser configurada
diretamente. `streamlit/requirements.txt` permanece como manifesto específico
do deploy no Streamlit; o desenvolvimento e o Actions usam `pyproject.toml` e
`uv.lock`.

### Agendamento diário no GitHub Actions

O workflow `.github/workflows/coleta-diaria.yml` roda todo dia às **06:17 de São
Paulo (09:17 UTC)** e também por `workflow_dispatch`. Execuções agendadas podem
atrasar; o arquivo precisa estar na branch padrão do repositório.

Em Settings → Secrets and variables → Actions, configure os Secrets:

- `WAREHOUSE_DATABASE_URL`: URL do Neon com `sslmode=require`.
- `OPENAI_API_KEY`: chave da API usada para gerar os embeddings.

O YAML referencia esses Secrets; os valores não devem ser versionados. O runner
não precisa do `.env`. Antes da primeira execução em uma base nova, aplique
`sql/001_criar_vagas_embeddings.sql` no banco, depois de criar `vagas_raw` pela
coleta. O workflow valida a presença das duas variáveis antes da coleta.

O job tem limite de **60 minutos** e executa:

1. Coleta e carga no Neon.
2. Transformação com dbt.
3. Geração incremental de `titulo_empresa_descricao`, com intervalo de 60 segundos
   entre lotes.
4. Limpeza dos embeddings com última observação conhecida anterior a 60 dias.

Os arquivos Python novos, o SQL e o `pyproject.toml` precisam estar versionados
na branch usada pelo workflow, junto com `uv.lock`. A instalação usa
`uv sync --locked`. A execução completa local inicial levou cerca de
25 minutos para os 25 lotes restantes; a duração diária depende das pendências.

Para disparar e acompanhar uma execução manual:

```bash
gh workflow run coleta-diaria.yml
gh run list --workflow coleta-diaria.yml
gh run view ID_DA_EXECUCAO --log
```

Escolhemos Actions para orquestrar esta sequência diária: ele oferece
agendamento, logs e Secrets sem manter servidor, scheduler, workers ou Redis.
Airflow acrescentava infraestrutura e exigia que a máquina local ficasse ligada.
O Compose agora contém somente um Postgres opcional para desenvolvimento, com
volume próprio (`vagas-db-volume`), preservando os volumes antigos.

Para concluir o aceite, acompanhe **três dias consecutivos** com evento `schedule`
e status de sucesso no Actions e confira a carga no Neon:

```sql
SELECT coletado_em::date AS dia, count(*) AS vagas_novas
FROM vagas_raw
GROUP BY 1 ORDER BY 1 DESC;
```

Uma execução bem-sucedida pode inserir zero registros se todas as vagas já
existirem; compare essa consulta com o log de coleta e inserção de cada execução.
Não usamos reset no workflow diário.

---

### Executar a coleta diretamente

Configure `WAREHOUSE_DATABASE_URL` no `.env` e execute na raiz do projeto:

```bash
uv run python src/collect.py
```

A execução coleta, remove IDs duplicados e grava diretamente no Postgres, sem
arquivo intermediário. Se não houver vagas válidas, levanta uma exceção e sai
com código diferente de zero antes de acessar o banco. Falhas por palavra-chave
continuam sendo registradas; resultados das demais palavras-chave são carregados.
As requisições usam uma Session com até três tentativas adicionais e espera
progressiva para falhas de conexão e HTTP 429, 500, 502, 503 e 504.

Para verificar o comportamento de falha sem editar o código:

```bash
GUPY_API_URL=https://portal.gupy.io/api/rota-invalida uv run python src/collect.py
echo $?
```

### Descrição da vaga

`vagas_raw.descricao` é uma coluna `TEXT` preenchida com o campo `description`
retornado na própria listagem da Gupy, sem chamada extra de detalhe. O texto é
preservado como recebido para extração de skills e busca semântica. A carga
adiciona a coluna automaticamente com `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`,
permitindo atualizar bancos existentes. Em registros existentes, `ON CONFLICT
DO UPDATE` atualiza os dados recebidos da vaga, incluindo título, descrição e
link, e avança `ultima_coleta`. `coletado_em`, a data de primeira inclusão, é
preservado. Campos vazios recebidos também substituem os valores anteriores.

Execute a coleta e depois `uv run python src/run_dbt.py` para atualizar as visões
usadas pelo dashboard. A rotina diária usa upsert e preserva as vagas já
armazenadas, sem reset. A ausência de uma vaga na coleta não a marca como fechada.

### Última vez que a vaga foi vista

`vagas_raw.ultima_coleta` (`TIMESTAMPTZ`, também exposta em `stg_vagas`) registra
quando o ID reapareceu na coleta. Novas vagas recebem a data atual; nas revisitas,
`DO UPDATE` avança esse campo sem alterar `coletado_em`, a primeira inclusão.
A migração mantém `NULL` em registros antigos até que sejam vistos novamente,
pois não existe um histórico confiável da última observação anterior.

Para encontrar vagas que não apareceram há sete dias:

```sql
SELECT id, nome, ultima_coleta
FROM vagas_raw
WHERE ultima_coleta < NOW() - INTERVAL '7 days'
ORDER BY ultima_coleta;
```

Registros com `ultima_coleta IS NULL` ainda não foram observados desde a
migração. Ausência não confirma fechamento: falhas por palavra-chave, alterações
na busca e o teto de 500 resultados podem impedir uma vaga de aparecer. O
pipeline não exclui nem marca essas vagas automaticamente como fechadas.

O log separa novas inserções de revisitas usando a diferença de `count(*)` antes
e depois do upsert. Um bloqueio transacional serializa as cargas na tabela para
que outras gravações não distorçam essa diferença; não usamos `rowcount`, que
representa apenas o último lote.

### Verificar a API da Gupy

```bash
curl -sS --fail-with-body --get 'https://portal.gupy.io/api/job-search/jobs' \
  --data-urlencode 'jobName=analista de dados' \
  --data-urlencode 'limit=100' \
  --data-urlencode 'offset=100' -o /tmp/gupy.json
python3 -m json.tool /tmp/gupy.json
```

O JSON contém `data` e `pagination` (`total`, `limit`, `offset`). O portal pode
retornar `total=100` mesmo quando há mais páginas. Por isso, o coletor avança o
`offset` pela quantidade recebida até uma página vazia, uma página sem IDs novos ou 500 vagas por
palavra-chave, com uma pausa de 0,5 segundo entre páginas. Os logs mostram cada
página e o acumulado por palavra-chave; erros preservam as páginas já coletadas
e permitem continuar com o próximo termo.

Para executar os testes de paginação:

```bash
uv run python -m unittest discover -s tests
```

Para verificar a carga, compare `SELECT count(*) FROM vagas_raw;` antes e depois
de executar o script. A contagem só aumenta se houver IDs novos. Nas revisitas,
`ON CONFLICT (id) DO UPDATE` atualiza os dados e `ultima_coleta` sem criar outra
linha nem alterar a data de primeira inclusão.

## 🧠 Embeddings das vagas — issue 7 em andamento

### Texto e configuração

Usamos `text-embedding-3-small`, com 1.536 dimensões e tokenização `cl100k_base`.
Cada vaga pode ter um vetor por variação e modelo; a chave primária é
`(vaga_id, variacao, modelo)`. A coluna `VECTOR(1536)` fixa a dimensão: mudar a
dimensão exige adaptar a estrutura, além de gerar novos vetores.

As variações disponíveis são `titulo` e `titulo_empresa_descricao`. A rotina
diária usa a segunda. A comparação com 20 consultas e a taxa de acerto no top 5
ainda estão pendentes; a escolha definitiva será feita após essa avaliação.

Antes da geração, entidades como `&amp;` e `&nbsp;` são decodificadas, os espaços
são normalizados e os campos são montados em ordem fixa. Essa normalização não
remove tags HTML. Campos opcionais vazios são omitidos; título vazio é inválido.
O SHA-256 é calculado sobre o texto preparado, exatamente como enviado ao modelo.
Mesmo texto, modelo e variação permitem reutilizar o vetor; alterações no texto
ou uma nova configuração exigem geração.

O teto é de **8.000 tokens por entrada**, sem corte automático. Entradas acima
dele são registradas como inválidas e ficam fora da geração; a execução continua
com as demais. No diagnóstico inicial de 578 vagas, a maior entrada completa
tinha 2.264 tokens, permitindo preservar as descrições inteiras. A política pode
ser revista com exemplos reais que ultrapassem o teto.

### Preparação e comandos locais

Após `uv sync --locked`, configure `WAREHOUSE_DATABASE_URL` e `OPENAI_API_KEY` no `.env`,
sem versionar seus valores. Os scripts de embeddings carregam esse arquivo com
`override=True`: localmente, ele tem prioridade sobre variáveis já definidas.
No Actions, sem esse arquivo, são usados os Secrets do ambiente.

Em uma base nova, execute a coleta para criar `vagas_raw` e aplique o conteúdo de
`sql/001_criar_vagas_embeddings.sql` no SQL Editor do Neon. Essa preparação ativa
a extensão `vector` e cria a tabela; ainda não gera vetores.

O exemplo didático de uma vaga está em `examples/`, separado da rotina diária.
Para executá-lo da raiz, use `uv run python -m examples.gerar_primeiro_embedding`.
Esse exemplo pode chamar a API e gravar um embedding; para uso diário, prefira
`src.gerar_embeddings`, que aplica a seleção por última observação.

```bash
# Diagnóstico: consulta o banco e conta tokens, sem chamar a API de embeddings.
uv run python -m src.gerar_embeddings
uv run python -m src.gerar_embeddings --max-lotes 1

# Execução: chama a API e grava os vetores; gera cobrança de uso.
uv run python -m src.gerar_embeddings --executar --max-lotes 1
uv run python -m src.gerar_embeddings --executar --intervalo 60

# Variação de título para a avaliação comparativa.
uv run python -m src.gerar_embeddings --variacao titulo
uv run python -m src.gerar_embeddings --executar --variacao titulo
```

São elegíveis apenas vagas com `ultima_coleta >= NOW() - INTERVAL '60 days'`.
Cada lote contém até **20 entradas** e **20.000 tokens**. O SDK permite até três
repetições além da tentativa inicial para falhas elegíveis. O intervalo padrão
de 60 segundos entre lotes é um ritmo inicial; os limites efetivos dependem da
conta e de outras chamadas simultâneas.

Os vetores são associados às entradas pelo `index` da resposta. Cada lote é
gravado em sua própria transação com upsert. Falhas na geração ou persistência
interrompem o processamento; os lotes já confirmados permanecem salvos e são
reconhecidos pelo hash na próxima execução. Isso não constitui uma garantia de
cobrança única: uma resposta perdida ou falha de persistência após a geração
pode exigir outra chamada.

Os logs registram modelo, variação, quantidade, tokens da resposta, custo
estimado e duração. O preço configurado é US$ 0,02 por milhão de tokens para o
modelo escolhido; deve ser revisto se o modelo ou a tarifa mudar. O consumo é
registrado antes da persistência, pois o rollback do banco não desfaz a API.

### Medições da geração inicial

Resultados observados localmente em **03/11/2026**, para a variação completa:

| Medida | Resultado |
|---|---:|
| Vagas elegíveis com embeddings atualizados | 538 |
| Pendências e entradas inválidas ao final | 0 |
| Tokens, somando os lotes dessas 538 vagas | 512.574 |
| Custo estimado desses lotes | US$ 0,01025148 |
| Embeddings totais armazenados | 539 |

O registro adicional veio do exercício inicial com uma vaga cuja
`ultima_coleta` era nula. Os custos acima não incluem esse exercício nem o texto
fictício usado para experimentar a API. Reexecutar o diagnóstico após a carga
reconheceu as 538 entradas atualizadas e não exigiu novas chamadas.

| Armazenamento | Antes | Depois |
|---|---:|---:|
| Banco inteiro, em bytes | 10.797.056 | 15.458.304 |
| Tabela de embeddings, incluindo índices e estruturas auxiliares, em bytes | 49.152 | 4.710.400 |
| Quantidade de embeddings | 1 | 539 |

O crescimento foi de **4.661.248 bytes** tanto no banco quanto na tabela nesse
intervalo. Dividido pelos 538 novos embeddings, representa **0,008664 MB por
embedding adicionado**. A média total da tabela foi de **0,008739 MB por
embedding**, incluindo espaço alocado. Usamos MB decimal: 1 MB = 1.000.000 bytes.
Como há uma variação por vaga nesta medição, esse é também o espaço médio dos
embeddings por vaga. Manter duas variações acrescentará outro vetor por vaga;
texto menor reduz tokens de geração, mas mantém as 1.536 dimensões.

Para repetir a medição, registre esta consulta antes e depois de uma carga:

```sql
SELECT
    NOW() AS medido_em,
    pg_database_size(current_database()) AS banco_bytes,
    pg_total_relation_size('public.vagas_embeddings') AS tabela_embeddings_bytes,
    COUNT(*) AS total_embeddings,
    COUNT(DISTINCT vaga_id) AS vagas_distintas
FROM public.vagas_embeddings;
```

Isolando o crescimento dos embeddings e descontando o banco atual, um orçamento
de 0,5 GB decimal comportaria aproximadamente 55.900 vetores adicionais. O Neon
anuncia atualmente 1 GB por projeto no plano gratuito, o que daria cerca de
113.600 vetores adicionais sob a mesma hipótese ([plano atual](https://neon.com/pricing),
[mudança da cota](https://neon.com/blog/neon-free-plan-1-gb-per-project)). Essas
projeções não incluem novas descrições, outros dados, índices futuros ou logs.
A duração real ainda depende da medição do crescimento líquido diário do banco:
`dias restantes ≈ MB disponíveis / crescimento líquido em MB por dia`.

### Limpeza e retenção

```bash
# Apenas conta candidatos, sem excluir.
uv run python -m src.limpar_embeddings

# Remove embeddings com última observação conhecida anterior a 60 dias.
uv run python -m src.limpar_embeddings --executar
```

A exclusão usa `DELETE ... USING vagas_raw` e afeta todas as variações e modelos
da vaga antiga, preservando `vagas_raw`. Vagas vistas há exatamente 60 dias são
preservadas pelo operador `<`. Registros com `ultima_coleta IS NULL` também são
preservados: uma data desconhecida não prova ausência por mais de 60 dias. Eles
ficam fora de novas gerações até reaparecerem na coleta.

No exercício SQL com tabelas temporárias e rollback, uma vaga vista há 61 dias
perdeu seus dois embeddings; as vagas com 60 dias, 59 dias e data nula mantiveram
seus vetores. A vaga original permaneceu após a exclusão. Na base real medida,
havia 539 embeddings, zero candidatos e um registro com observação desconhecida;
diagnóstico e execução removeram zero registros.

A limpeza deixa espaço disponível para reutilização pelo PostgreSQL; a redução
física imediata do tamanho da tabela não é garantida. As medições de crescimento
e retenção precisam ser acompanhadas ao longo do tempo.

A busca por cosseno com filtros, os links no resultado e a avaliação de top 5
das duas variações são as próximas etapas da issue 7. As issues de assistente e
avaliação de RAG ainda não estão implementadas.

## 🗄️ Modelos dbt

### Silver — `stg_vagas`
Limpeza e padronização da camada bruta:
- Padronização de texto com `initcap` e `trim`
- Classificação de senioridade (Júnior, Pleno, Sênior, Especialista, Estágio)
- Classificação de regime (Remoto, Híbrido, Presencial)
- Tratamento de nulos com `nullif`
- Classificação `area` pelo título: MLOps, Machine Learning, Engenharia de IA, IA — outras funções, Dados e Outras áreas

### Gold — modelos analíticos
| Modelo | Descrição |
|---|---|
| `vagas_por_estado` | Distribuição geográfica das vagas |
| `vagas_por_senioridade` | Distribuição por nível com percentual |
| `vagas_por_empresa` | Top empresas que mais contratam |
| `vagas_por_area` | Distribuição por área de atuação |

---

## 🔍 Cargos monitorados

```
Engenheiro de Dados · Data Engineer
Cientista de Dados · Data Scientist
Analista de Dados · Data Analyst
Analytics Engineer · Data Quality
Arquiteto de Dados · Data Architect
```

---

As buscas também incluem `machine learning`, `engenheiro de machine learning`,
`machine learning engineer`, `engenheiro de IA`, `AI engineer`, `AI engineering`,
`inteligência artificial`, `artificial intelligence`, `MLOps`, `LLMOps`,
`generative AI`, `IA generativa`, `GenAI` e `aprendizado de máquina`.
As buscas podem se sobrepor; a carga deduplica por ID antes de inserir.

A área é uma classificação heurística do título, não da descrição. MLOps/LLMOps
precedem Machine Learning, que precede IA e Dados. Siglas como IA e AI só casam
como palavras inteiras; títulos sem correspondência ficam em `Outras áreas`.
Títulos com IA sem indicação de engenharia, desenvolvimento, arquitetura ou
liderança técnica ficam em `IA — outras funções` (por exemplo, governança ou
advocacia). Essa separação evita contar toda menção a IA como engenharia.
Vagas de Data Science continuam em Dados, salvo menção explícita a ML ou IA.
O panorama inclui um gráfico por área e a exploração oferece o filtro `Área`.
Não é necessário resetar o banco; o dbt classifica também os registros existentes.

Para testar as regras de classificação, após executar a transformação:

```bash
uv run dbt test --project-dir dbt/vagas --profiles-dir dbt/vagas
```

Esse comando requer as variáveis `PG*` do perfil configuradas no ambiente.
O workflow mantém o teto de 500 vagas por termo e o timeout de 60 minutos;
acompanhe os logs ao ampliar os termos para conferir duração e possíveis cortes.

## 👤 Autor

**Mateus Virginio**
[GitHub](https://github.com/mateusvirginio) · [Dashboard](https://vagas-pipeline.streamlit.app)
