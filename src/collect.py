import requests
import json
import os
import logging
import time
from datetime import datetime

import psycopg2
from psycopg2.extras import execute_values

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -------------------------------------------------------------------
# Configurações
# -------------------------------------------------------------------
GUPY_API_URL = "https://portal.gupy.io/api/job-search/jobs"
GUPY_PAGE_SIZE = 100
GUPY_MAX_JOBS_PER_KEYWORD = 500
GUPY_PAGE_DELAY_SECONDS = 0.5
DATA_DIR = "/opt/airflow/logs/raw_data"

WAREHOUSE_URL = os.environ["WAREHOUSE_DATABASE_URL"]

KEYWORDS = [
    "engenheiro de dados",
    "data engineer",
    "cientista de dados",
    "data scientist",
    "analista de dados",
    "data analyst",
    "analytics engineer",
    "data quality",
    "arquiteto de dados",
    "data architect",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def _fetch_gupy() -> list[dict]:
    all_jobs = []
    for keyword in KEYWORDS:
        logger.info(f"[Gupy] Coletando: '{keyword}'")
        collected = 0
        seen_ids = set()
        try:
            while collected < GUPY_MAX_JOBS_PER_KEYWORD:
                limit = min(GUPY_PAGE_SIZE, GUPY_MAX_JOBS_PER_KEYWORD - collected)
                params = {"jobName": keyword, "limit": limit, "offset": collected}
                response = requests.get(GUPY_API_URL, params=params, headers=HEADERS, timeout=30)
                response.raise_for_status()
                payload = response.json()
                jobs = payload.get("data", [])[:limit]
                total = payload.get("pagination", {}).get("total")
                logger.info(
                    f"[Gupy] '{keyword}' | offset={collected} | "
                    f"página={len(jobs)} | total disponível={total}"
                )
                if not jobs:
                    break
                page_ids = {job.get("id") for job in jobs if job.get("id") is not None}
                if not page_ids - seen_ids:
                    logger.warning(
                        f"[Gupy] '{keyword}' | offset={collected} | "
                        "página sem IDs novos; encerrando paginação"
                    )
                    break
                seen_ids.update(page_ids)
                for job in jobs:
                    all_jobs.append({
                        "id": f"gupy_{job.get('id')}",
                        "nome": job.get("name"),
                        "empresa": job.get("careerPageName"),
                        "cidade": job.get("city"),
                        "estado": job.get("state"),
                        "tipo_contrato": job.get("type"),
                        "regime": job.get("workplaceType"),
                        "publicado_em": job.get("publishedDate"),
                        "url": job.get("jobUrl"),
                        "fonte": "gupy",
                    })
                collected += len(jobs)
                # O portal pode informar total=100 mesmo com páginas posteriores.
                # Encerramos por página vazia, ausência de IDs novos ou teto.
                if collected >= GUPY_MAX_JOBS_PER_KEYWORD:
                    break
                time.sleep(GUPY_PAGE_DELAY_SECONDS)
        except requests.RequestException as e:
            logger.error(f"[Gupy] Erro para '{keyword}': {e}")
        logger.info(f"[Gupy] '{keyword}' → {collected} vagas coletadas")
    return all_jobs


def fetch_vagas(**context):
    os.makedirs(DATA_DIR, exist_ok=True)

    gupy_jobs = _fetch_gupy()
    all_jobs = gupy_jobs

    seen_ids = set()
    unique_jobs = []
    for job in all_jobs:
        job_id = job.get("id")
        if job_id and job_id not in seen_ids:
            seen_ids.add(job_id)
            unique_jobs.append(job)

    logger.info(f"Total coletado: {len(all_jobs)} | Únicos: {len(unique_jobs)}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(DATA_DIR, f"vagas_{timestamp}.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(unique_jobs, f, ensure_ascii=False, indent=2)

    logger.info(f"Arquivo salvo: {filepath}")
    return filepath


def save_to_postgres(**context):
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

    conn = psycopg2.connect(WAREHOUSE_URL)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS vagas_raw (
            id              VARCHAR(100) PRIMARY KEY,
            nome            VARCHAR(500),
            empresa         VARCHAR(500),
            cidade          VARCHAR(200),
            estado          VARCHAR(100),
            tipo_contrato   VARCHAR(100),
            regime          VARCHAR(100),
            publicado_em    VARCHAR(100),
            url             TEXT,
            fonte           VARCHAR(50),
            coletado_em     TIMESTAMP DEFAULT NOW()
        )
    """)

    rows = [
        (
            job.get("id"), job.get("nome"), job.get("empresa"),
            job.get("cidade"), job.get("estado"), job.get("tipo_contrato"),
            job.get("regime"), job.get("publicado_em"), job.get("url"), job.get("fonte"),
        )
        for job in jobs
    ]

    execute_values(
        cur,
        """
        INSERT INTO vagas_raw
            (id, nome, empresa, cidade, estado, tipo_contrato,
             regime, publicado_em, url, fonte)
        VALUES %s
        ON CONFLICT (id) DO NOTHING
        """,
        rows,
    )

    inserted = cur.rowcount
    conn.commit()
    cur.close()
    conn.close()
    logger.info(f"{inserted} novas vagas inseridas | {len(rows) - inserted} já existiam.")
