from airflow.decorators import dag, task
from datetime import datetime, timedelta
from src.collect import fetch_vagas, save_to_postgres

@dag(
    dag_id="pipeline_vagas_dados",
    start_date=datetime(2026, 1, 1),
    schedule_interval="@daily",
    catchup=False,
    tags=["vagas", "dados", "etl"],
)
def pipeline_vagas():

    @task
    def coletar():
        fetch_vagas()

    @task
    def salvar():
        save_to_postgres()

    coletar() >> salvar()

dag = pipeline_vagas()