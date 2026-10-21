from airflow.decorators import dag, task
from datetime import datetime
from src.collect import main

@dag(
    dag_id="pipeline_vagas_dados",
    start_date=datetime(2026, 1, 1),
    schedule_interval="@daily",
    catchup=False,
    tags=["vagas", "dados", "etl"],
)
def pipeline_vagas():

    @task
    def coletar_e_salvar():
        main()

    coletar_e_salvar()

dag = pipeline_vagas()
