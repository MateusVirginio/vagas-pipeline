# 📊 Vagas Pipeline — Mercado de Dados no Brasil

![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)
![Apache Airflow](https://img.shields.io/badge/Apache%20Airflow-2.9.2-017CEE?logo=apacheairflow)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791?logo=postgresql)
![dbt](https://img.shields.io/badge/dbt-1.11-FF694B?logo=dbt)
![Streamlit](https://img.shields.io/badge/Streamlit-online-FF4B4B?logo=streamlit)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)

Pipeline de dados **end-to-end** com arquitetura Medallion que coleta, transforma e visualiza vagas da área de dados no Brasil diariamente.

🔗 **[Dashboard ao vivo](https://vagas-pipeline.streamlit.app)**

---

## 🎯 Problema resolvido

O mercado de dados no Brasil cresce rapidamente, mas é difícil ter uma visão consolidada das vagas abertas, empresas que mais contratam e distribuição por senioridade e região. Este pipeline coleta automaticamente vagas de Engenheiro de Dados, Cientista de Dados, Analista de Dados e outros cargos da área, centralizando tudo em um dashboard interativo atualizado diariamente.

---

## 🏗️ Arquitetura Medallion

```
        ┌────────────────┐
        │    API Gupy    │
        └────────┬───────┘
                 ▼
        ┌────────────────┐
        │ Python+Airflow │  Orquestração diária
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
        └────────┬───────┘
                 ▼
        ┌────────────────┐
        │   Streamlit    │  Dashboard publicado online
        └────────────────┘
```

O script coleta e grava na mesma execução. A DAG existente chama esse script em uma única task:

```
coletar_e_salvar
```

---

## 🛠️ Stack

| Camada | Tecnologia | Função |
|---|---|---|
| Orquestração | Apache Airflow 2.9 | Agendamento e monitoramento do pipeline |
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
├── dags/
│   └── pipeline_vagas.py        # DAG do Airflow com @task decorator
├── src/
│   ├── __init__.py
│   └── collect.py               # Extract (Gupy) e Load
├── dbt/
│   └── vagas/
│       └── models/
│           ├── staging/
│           │   ├── sources.yml
│           │   └── stg_vagas.sql        # Silver: limpeza e padronização
│           └── marts/
│               ├── vagas_por_estado.sql
│               ├── vagas_por_senioridade.sql
│               └── vagas_por_empresa.sql
├── streamlit/
│   └── app.py                   # Dashboard interativo
├── docker-compose.yaml
├── pyproject.toml
└── .gitignore
```

---

## 🚀 Como rodar localmente

### Pré-requisitos
- Docker e Docker Compose
- UV (`pip install uv`)

### 1. Clone o repositório
```bash
git clone https://github.com/mateusvirginio/vagas-pipeline.git
cd vagas-pipeline
```

### 2. Configure o ambiente
```bash
echo "AIRFLOW_UID=$(id -u)" > .env
uv sync
source .venv/bin/activate
```

### 3. Sobe o Airflow
```bash
docker compose up airflow-init
docker compose up -d
```

Acesse http://localhost:8080 — usuário e senha: `airflow`

### 4. Rode as transformações dbt
```bash
cd dbt/vagas
dbt run
```

### 5. Sobe o dashboard
```bash
cd ../..
streamlit run streamlit/app.py
```

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
de executar a DAG. A contagem só aumenta se houver IDs novos, pois a carga usa
`ON CONFLICT (id) DO NOTHING`.

## 🗄️ Modelos dbt

### Silver — `stg_vagas`
Limpeza e padronização da camada bruta:
- Padronização de texto com `initcap` e `trim`
- Classificação de senioridade (Júnior, Pleno, Sênior, Especialista, Estágio)
- Classificação de regime (Remoto, Híbrido, Presencial)
- Tratamento de nulos com `nullif`

### Gold — modelos analíticos
| Modelo | Descrição |
|---|---|
| `vagas_por_estado` | Distribuição geográfica das vagas |
| `vagas_por_senioridade` | Distribuição por nível com percentual |
| `vagas_por_empresa` | Top empresas que mais contratam |

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

## 👤 Autor

**Mateus Virginio**
[GitHub](https://github.com/mateusvirginio) · [Dashboard](https://vagas-pipeline.streamlit.app)
