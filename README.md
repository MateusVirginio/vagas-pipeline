# 📊 Vagas Pipeline — Pipeline de Vagas de Dados no Brasil

![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)
![Apache Airflow](https://img.shields.io/badge/Apache%20Airflow-2.9.2-017CEE?logo=apacheairflow)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791?logo=postgresql)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)

Pipeline de dados **end-to-end** que coleta, processa e armazena vagas da área de dados no Brasil diariamente via API do Gupy.

---

## 🎯 Problema resolvido

O mercado de dados no Brasil cresce rapidamente, mas é difícil ter uma visão consolidada das vagas abertas, skills mais demandadas e regiões com mais oportunidades. Este pipeline coleta automaticamente vagas de cargos como Engenheiro de Dados, Cientista de Dados e Analista de Dados, centralizando tudo em um banco de dados pronto para análise.

---

## 🏗️ Arquitetura

```
┌─────────────┐     ┌──────────────┐     ┌────────────────┐     ┌──────────────┐
│   API Gupy  │────▶│    Python    │────▶│ Apache Airflow │────▶│  PostgreSQL  │
│  (source)   │     │  (coleta)    │     │ (orquestração) │     │ (armazena)   │
└─────────────┘     └──────────────┘     └────────────────┘     └──────────────┘
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
| Coleta | Python + Requests | Consumo da API do Gupy |
| Processamento | Pandas | Limpeza e deduplicação dos dados |
| Armazenamento | PostgreSQL 15 | Persistência das vagas coletadas |
| Infraestrutura | Docker + Compose | Ambiente reproduzível e isolado |
| Gerenciamento | UV | Gerenciamento de dependências Python |

---

## 📁 Estrutura do projeto

```
vagas-pipeline/
├── dags/
│   └── pipeline_vagas.py   # DAG do Airflow com @task decorator
├── src/
│   ├── __init__.py
│   └── collect.py          # Lógica de coleta (Extract) e carga (Load)
├── docker-compose.yaml     # Airflow + PostgreSQL + Redis
├── pyproject.toml          # Dependências gerenciadas pelo UV
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
# Cria o .env com seu UID (obrigatório no Linux)
echo "AIRFLOW_UID=$(id -u)" > .env

# Instala as dependências Python
uv sync
```

### 3. Inicializa o Airflow
```bash
docker compose up airflow-init
```
Aguarda a mensagem: `User "airflow" created with role "Admin"`

### 4. Sobe os serviços
```bash
docker compose up -d
```

### 5. Acesse o painel
- URL: http://localhost:8080
- Usuário: `airflow`
- Senha: `airflow`

Ative a DAG `pipeline_vagas_dados` e clique em ▶️ para o primeiro run.

---

## 🗄️ Estrutura dos dados

```sql
CREATE TABLE vagas_raw (
    id            BIGINT PRIMARY KEY,
    nome          VARCHAR(500),   -- título da vaga
    empresa       VARCHAR(500),
    cidade        VARCHAR(200),
    estado        VARCHAR(100),
    tipo_contrato VARCHAR(100),
    regime        VARCHAR(100),   -- remoto, híbrido, presencial
    publicado_em  TIMESTAMP,
    url           TEXT,
    coletado_em   TIMESTAMP DEFAULT NOW()
);
```

### Exemplos de vagas coletadas

| Cargo | Empresa | Estado |
|---|---|---|
| Engenheiro de Dados | — | SP |
| Cientista de Dados | — | RJ |
| Analista de Dados \| Azure | — | MG |
| Data Engineer \| Home-Office | — | Remoto |

---

## 🔍 Keywords monitoradas

```python
"engenheiro de dados", "data engineer",
"cientista de dados", "data scientist",
"analista de dados", "data analyst",
"analytics engineer", "data quality",
"arquiteto de dados", "data architect"
```

---

## 📈 Próximos passos

- [ ] Camada de transformação com **dbt** (modelos analíticos sobre `vagas_raw`)
- [ ] Dashboard interativo com **Streamlit** publicado online
- [ ] Deploy na **AWS** (S3 + RDS + MWAA)
- [ ] Análise de skills mais demandadas por região

---