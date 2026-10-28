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

O workflow coleta e grava no Neon, depois executa `dbt run`. Se a coleta falhar,
a transformação não é executada.

---

## 🛠️ Stack

| Camada | Tecnologia | Função |
|---|---|---|
| Agendamento | GitHub Actions | Execução diária e disparo manual com logs |
| Coleta | Python + Requests | API Gupy |
| Armazenamento | PostgreSQL 15 | Persistência das vagas coletadas |
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
│   └── run_dbt.py               # dbt com credenciais de ambiente
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
├── pyproject.toml
└── .gitignore
```

---

## 🚀 Como rodar localmente

### Ambiente local

Instale Python 3.12 e UV. Na raiz do repositório:

```bash
uv sync
```

Configure `WAREHOUSE_DATABASE_URL` no `.env` com a URL do Neon (incluindo
`sslmode=require`). O arquivo não deve ser versionado.

Para desenvolver em um banco local opcional:

```bash
docker compose up -d postgres
# No .env, use WAREHOUSE_DATABASE_URL=postgresql://vagas:vagas@localhost:5432/vagas?sslmode=disable
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

### Agendamento diário no GitHub Actions

O workflow `.github/workflows/coleta-diaria.yml` roda todo dia às **06:17 de São
Paulo (09:17 UTC)** e também por `workflow_dispatch`. Execuções agendadas podem
atrasar; o arquivo precisa estar na branch padrão do repositório.

Em Settings → Secrets and variables → Actions, configure o Secret
`WAREHOUSE_DATABASE_URL` com a URL do Neon. Nunca coloque essa URL no YAML.
Para disparar e acompanhar uma execução manual:

```bash
gh workflow run coleta-diaria.yml
gh run list --workflow coleta-diaria.yml
gh run view ID_DA_EXECUCAO --log
```

Escolhemos Actions porque há apenas um script diário seguido de dbt: ele oferece
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
permitindo atualizar bancos existentes. Em registros existentes, `ON CONFLICT DO UPDATE` atualiza apenas
`ultima_coleta`, preservando os demais campos e a data de primeira inclusão.

Após o reset inicial com `TRUNCATE vagas_raw`, execute a coleta e depois
`uv run python src/run_dbt.py` para atualizar as visões usadas pelo dashboard.
O reset é uma operação manual; executar o coletor normalmente preserva as vagas
já armazenadas. A ausência de uma vaga na coleta não a marca como fechada.

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
de executar o script. A contagem só aumenta se houver IDs novos, pois a carga usa
`ON CONFLICT (id) DO UPDATE` altera somente `ultima_coleta` nas revisitas.

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
O workflow mantém o teto de 500 vagas por termo e o timeout de 30 minutos;
acompanhe os logs ao ampliar os termos para conferir duração e possíveis cortes.

## 👤 Autor

**Mateus Virginio**
[GitHub](https://github.com/mateusvirginio) · [Dashboard](https://vagas-pipeline.streamlit.app)
