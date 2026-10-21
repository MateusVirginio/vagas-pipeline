"""Teste real em tabelas temporárias; requer TEST_DATABASE_URL."""
import os
import unittest
from contextlib import nullcontext
from unittest.mock import patch

import psycopg2
from psycopg2.extras import execute_values

from src import collect


@unittest.skipUnless(os.getenv("TEST_DATABASE_URL"), "Defina TEST_DATABASE_URL para testar no Postgres")
class InsertCountTests(unittest.TestCase):
    def test_log_matches_count_across_batches_and_conflicts(self):
        with collect.closing(psycopg2.connect(os.environ["TEST_DATABASE_URL"])) as conn:
            with conn.cursor() as cur:
                cur.execute("CREATE TEMP TABLE old_insert_count (id integer PRIMARY KEY)")
                execute_values(cur, "INSERT INTO old_insert_count VALUES %s", [(i,) for i in range(250)])
                old_count = cur.rowcount
                cur.execute("SELECT count(*) FROM old_insert_count")
                actual_count = cur.fetchone()[0]
                self.assertEqual(old_count, 50)
                self.assertEqual(actual_count, 250)
                print(f"Reprodução antiga: rowcount={old_count}, count(*)={actual_count}")

                # A tabela temporária sombreia a tabela real só nesta conexão.
                cur.execute("""
                    CREATE TEMP TABLE vagas_raw (
                        id text PRIMARY KEY, nome text, empresa text, cidade text,
                        estado text, tipo_contrato text, regime text, publicado_em text,
                        url text, fonte text, coletado_em timestamp DEFAULT NOW()
                    )
                """)
            jobs = [{"id": f"teste_{i}", "nome": "Vaga de teste", "fonte": "gupy", "descricao": "Descrição de teste"} for i in range(250)]
            with patch.object(collect.psycopg2, "connect", return_value=conn), \
                    patch.object(collect, "closing", side_effect=nullcontext):
                for expected in (250, 0):
                    with conn.cursor() as cur:
                        cur.execute("SELECT count(*) FROM vagas_raw")
                        before = cur.fetchone()[0]
                    with self.assertLogs(collect.logger, level="INFO") as logs:
                        collect.save_to_postgres(jobs)
                    with conn.cursor() as cur:
                        cur.execute("SELECT count(*) FROM vagas_raw")
                        after = cur.fetchone()[0]
                    with conn.cursor() as cur:
                        cur.execute("SELECT count(*) FROM vagas_raw WHERE descricao = 'Descrição de teste'")
                        self.assertEqual(cur.fetchone()[0], 250)
                    logged = int(logs.output[-1].split(":", 2)[-1].split()[0])
                    self.assertEqual(logged, after - before)
                    self.assertEqual(logged, expected)
                    print(f"Carga corrigida: log={logged}, diferença de count(*)={after - before}")


if __name__ == "__main__":
    unittest.main()
