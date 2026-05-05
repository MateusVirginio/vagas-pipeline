import requests
import json
import os
import logging
import re
from datetime import datetime

from bs4 import BeautifulSoup
import psycopg2
from psycopg2.extras import execute_values

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -------------------------------------------------------------------
# Configurações
# -------------------------------------------------------------------
GUPY_API_URL = "https://portal.api.gupy.io/api/v1/jobs"
LINKEDIN_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
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
        try:
            params = {"jobName": keyword, "limit": 100, "offset": 0}
            response = requests.get(GUPY_API_URL, params=params, headers=HEADERS, timeout=30)
            response.raise_for_status()
            jobs = response.json().get("data", [])
            for job in jobs:
                all_jobs.append({
                    "id": f"gupy_{job.get('id')}",
                    "nome": job.get("name"),
                    "empresa": job.get("careerPageName"),
                    "cidade": job.get("city"),
                    "estado": job.get("state"),
                    "tipo_contrato": job.get("contractType"),
                    "regime": job.get("workplaceType"),
                    "publicado_em": job.get("publishedDate"),
                    "url": job.get("jobUrl"),
                    "fonte": "gupy",
                })
            logger.info(f"  → {len(jobs)} vagas encontradas")
        except requests.RequestException as e:
            logger.error(f"[Gupy] Erro para '{keyword}': {e}")
    return all_jobs


def _fetch_linkedin() -> list[dict]:
    all_jobs = []
    for keyword in KEYWORDS:
        logger.info(f"[LinkedIn] Coletando: '{keyword}'")
        try:
            params = {
                "keywords": keyword,
                "location": "Brasil",
                "geoId": "106057199",  # ID do Brasil no LinkedIn
                "start": 0,
            }
            response = requests.get(LINKEDIN_URL, params=params, headers=HEADERS, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            cards = soup.find_all("div", class_="base-search-card")

            for card in cards:
                urn = card.get("data-entity-urn", "")
                job_id_match = re.search(r"\d+", urn)
                job_id = f"linkedin_{job_id_match.group()}" if job_id_match else None
                if not job_id:
                    continue

                title_tag = card.find("h3", class_="base-search-card__title")
                nome = title_tag.get_text(strip=True) if title_tag else None

                company_tag = card.find("h4", class_="base-search-card__subtitle")
                empresa = company_tag.get_text(strip=True) if company_tag else None

                location_tag = card.find("span", class_="job-search-card__location")
                localizacao = location_tag.get_text(strip=True) if location_tag else None

                cidade, estado = None, None
                if localizacao:
                    partes = [p.strip() for p in localizacao.split(",")]
                    if len(partes) >= 2:
                        cidade = partes[0]
                        estado = partes[1]

                date_tag = card.find("time")
                publicado_em = date_tag.get("datetime") if date_tag else None

                link_tag = card.find("a", class_="base-card__full-link")
                url = link_tag.get("href") if link_tag else None

                all_jobs.append({
                    "id": job_id,
                    "nome": nome,
                    "empresa": empresa,
                    "cidade": cidade,
                    "estado": estado,
                    "tipo_contrato": None,
                    "regime": None,
                    "publicado_em": publicado_em,
                    "url": url,
                    "fonte": "linkedin",
                })

            logger.info(f"  → {len(cards)} vagas encontradas")

        except requests.RequestException as e:
            logger.error(f"[LinkedIn] Erro para '{keyword}': {e}")

    return all_jobs


def fetch_vagas(**context):
    os.makedirs(DATA_DIR, exist_ok=True)

    gupy_jobs = _fetch_gupy()
    linkedin_jobs = _fetch_linkedin()
    all_jobs = gupy_jobs + linkedin_jobs

    seen_ids = set()
    unique_jobs = []
    for job in all_jobs:
        job_id = job.get("id")
        if job_id and job_id not in seen_ids:
            seen_ids.add(job_id)
            unique_jobs.append(job)

    logger.info(f"Total coletado: {len(all_jobs)} | Únicos: {len(unique_jobs)}")
    logger.info(f"  Gupy: {len(gupy_jobs)} | LinkedIn: {len(linkedin_jobs)}")

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

    conn = psycopg2.connect(**DB_CONFIG)
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