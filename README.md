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
┌──────────────┐   ┌──────────────┐
│   API Gupy   │   │   LinkedIn   │
└──────┬───────┘   └──────┬───────┘
       └─────────┬─────────┘
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

A DAG executa diariamente com duas tasks em sequência:

```
coletar_vagas  ──▶  salvar_no_postgres
```

---

## 🛠️ Stack

| Camada | Tecnologia | Função |
|---|---|---|
| Orquestração | Apache Airflow 2.9 | Agendamento e monitoramento do pipeline |
| Coleta | Python + Requests + BeautifulSoup | API Gupy + scraping LinkedIn |
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
│   └── collect.py               # Extract (Gupy + LinkedIn) e Load
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
| `vagas_por_estado` | Distribuição geográfica com breakdown por fonte |
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
[LinkedIn](https://linkedin.com/in/mateusvirginio) · [GitHub](https://github.com/mateusvirginio) · [Dashboard](https://vagas-pipeline.streamlit.app)