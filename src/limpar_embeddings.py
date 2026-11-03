import argparse
import os
from contextlib import closing

import psycopg2
from dotenv import load_dotenv


def limpar_embeddings(conn, executar=False):
    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    COUNT(*),
                    COUNT(*) FILTER (
                        WHERE v.ultima_coleta
                            < NOW() - INTERVAL '60 days'
                    ),
                    COUNT(*) FILTER (
                        WHERE v.ultima_coleta IS NULL
                    )
                FROM public.vagas_embeddings AS e
                JOIN public.vagas_raw AS v
                    ON v.id = e.vaga_id
            """)
            total, candidatos, desconhecidos = cur.fetchone()

            removidos = 0

            if executar:
                cur.execute("""
                    DELETE FROM public.vagas_embeddings AS e
                    USING public.vagas_raw AS v
                    WHERE e.vaga_id = v.id
                      AND v.ultima_coleta
                          < NOW() - INTERVAL '60 days'
                """)
                removidos = cur.rowcount

    return {
        "total_antes": total,
        "candidatos": candidatos,
        "observacao_desconhecida": desconhecidos,
        "removidos": removidos,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Remove embeddings de vagas não vistas há mais de 60 dias."
    )
    parser.add_argument("--executar", action="store_true")
    args = parser.parse_args()

    load_dotenv(dotenv_path=".env", override=True)

    with closing(
        psycopg2.connect(os.environ["WAREHOUSE_DATABASE_URL"])
    ) as conn:
        resultado = limpar_embeddings(conn, executar=args.executar)

    print("Modo:", "execução" if args.executar else "diagnóstico")

    for nome, valor in resultado.items():
        print(f"{nome}: {valor}")


if __name__ == "__main__":
    main()