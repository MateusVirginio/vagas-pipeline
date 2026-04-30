import requests
import json
import os
import logging
from datetime import datetime

import psycopg2
from psycopg2.extras import execute_values

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -------------------------------------------------------------------
# Configurações
# -------------------------------------------------------------------
GUPY_API_URL = "https://portal.api.gupy.io/api/v1/jobs"
DATA_DIR = "/opt/airflow/logs/raw_data"

DB_CONFIG = {
    "host": "postgres",
    "database": "airflow",
    "user": "airflow",
    "password": "airflow",
    "port": 5432,
}

KEYWORDS = [
    "engenheiro de dados",
    "data engineer",
    "cientista de dados",
    "data scientist",
    "analista de dados",
    "data analyst",
    "analytics engineer",
    "engenheiro analytics",
    "data quality",
    "arquiteto de dados",
    "data architect",
]


# -------------------------------------------------------------------
# Task 1: Coleta
# -------------------------------------------------------------------
def fetch_vagas(**context):
    """
    Coleta vagas de dados na API do Gupy para cada keyword
    e persiste o JSON bruto em /opt/airflow/logs/raw_data/.
    """
    os.makedirs(DATA_DIR, exist_ok=True)
    all_jobs = []

    for keyword in KEYWORDS:
        logger.info(f"Coletando vagas para: '{keyword}'")
        try:
            params = {"jobName": keyword, "limit": 100, "offset": 0}
            response = requests.get(GUPY_API_URL, params=params, timeout=30)
            response.raise_for_status()
            jobs = response.json().get("data", [])
            all_jobs.extend(jobs)
            logger.info(f"  → {len(jobs)} vagas encontradas")
        except requests.RequestException as e:
            logger.error(f"Erro na requisição para '{keyword}': {e}")

    # Remove duplicatas por ID
    seen_ids = set()
    unique_jobs = []
    for job in all_jobs:
        job_id = job.get("id")
        if job_id not in seen_ids:
            seen_ids.add(job_id)
            unique_jobs.append(job)

    logger.info(f"Total único coletado: {len(unique_jobs)} vagas")

    # Salva o raw
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(DATA_DIR, f"vagas_{timestamp}.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(unique_jobs, f, ensure_ascii=False, indent=2)

    logger.info(f"Arquivo salvo: {filepath}")
    return filepath


# -------------------------------------------------------------------
# Task 2: Carga no PostgreSQL
# -------------------------------------------------------------------
def save_to_postgres(**context):
    """
    Lê o arquivo JSON mais recente e carrega as vagas
    na tabela vagas_raw do banco do Airflow.
    """
    files = sorted(
        [os.path.join(DATA_DIR, f) for f in os.listdir(DATA_DIR) if f.endswith(".json")]
    )

    if not files:
        logger.warning("Nenhum arquivo JSON encontrado.")
        return

    latest_file = files[-1]
    logger.info(f"Processando: {latest_file}")

    with open(latest_file, "r", encoding="utf-8") as f:
        jobs = json.load(f)

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS vagas_raw (
            id              BIGINT PRIMARY KEY,
            nome            VARCHAR(500),
            empresa         VARCHAR(500),
            cidade          VARCHAR(200),
            estado          VARCHAR(100),
            tipo_contrato   VARCHAR(100),
            regime          VARCHAR(100),
            publicado_em    TIMESTAMP,
            url             TEXT,
            coletado_em     TIMESTAMP DEFAULT NOW()
        )
    """)

    rows = [
        (
            job.get("id"),
            job.get("name"),
            job.get("careerPageName"),
            job.get("city"),
            job.get("state"),
            job.get("contractType"),
            job.get("workplaceType"),
            job.get("publishedDate"),
            job.get("jobUrl"),
        )
        for job in jobs
    ]

    execute_values(
        cur,
        """
        INSERT INTO vagas_raw
            (id, nome, empresa, cidade, estado, tipo_contrato, regime, publicado_em, url)
        VALUES %s
        ON CONFLICT (id) DO NOTHING
        """,
        rows,
    )

    conn.commit()
    cur.close()
    conn.close()
    logger.info(f"{len(rows)} vagas inseridas no PostgreSQL.")