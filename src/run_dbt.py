"""Executa dbt run com o perfil versionado e a mesma URL usada pelo coletor."""
import os
from pathlib import Path
import subprocess

from dotenv import load_dotenv
from psycopg2.extensions import parse_dsn


def main():
    load_dotenv()
    credentials = parse_dsn(os.environ["WAREHOUSE_DATABASE_URL"])
    env = os.environ.copy()
    for key, variable in {
        "host": "PGHOST", "port": "PGPORT", "user": "PGUSER",
        "password": "PGPASSWORD", "dbname": "PGDATABASE", "sslmode": "PGSSLMODE",
    }.items():
        if key in credentials:
            env[variable] = credentials[key]
    project = Path(__file__).resolve().parents[1] / "dbt" / "vagas"
    subprocess.run(
        ["dbt", "run", "--project-dir", str(project), "--profiles-dir", str(project)],
        env=env, check=True,
    )


if __name__ == "__main__":
    main()
