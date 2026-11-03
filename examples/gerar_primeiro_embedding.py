"""Exemplo didático: python -m examples.gerar_primeiro_embedding."""

import json
import os
from contextlib import closing

import psycopg2
from dotenv import load_dotenv
from openai import OpenAI
from psycopg2.extras import RealDictCursor

from src.embedding_text import (
    calcular_hash,
    preparar_texto,
    validar_texto
)

MODELO = "text-embedding-3-small"
VARIACAO = "titulo_empresa_descricao"

def main():
    load_dotenv(dotenv_path=".env", override=True)

    with closing(
        psycopg2.connect(os.environ["WAREHOUSE_DATABASE_URL"])
    ) as conn:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT id, nome, empresa, descricao
                    FROM public.vagas_raw
                    WHERE NULLIF(TRIM(nome), '') IS NOT NULL
                    ORDER BY id
                    LIMIT 1
                    """
                )
                vaga = cur.fetchone()

                if vaga is None:
                    raise RuntimeError("Nenhuma vaga disponível.")

                texto = preparar_texto(vaga, VARIACAO)
                validar_texto(texto)
                texto_hash = calcular_hash(texto)

                cur.execute(
                    """
                    SELECT texto_hash
                    FROM public.vagas_embeddings
                    WHERE vaga_id = %s
                        AND variacao = %s
                        AND modelo = %s
                    """, (vaga["id"], VARIACAO, MODELO))

                existente = cur.fetchone()


        if existente and existente["texto_hash"] == texto_hash:
            print("Embedding já atualizado:", vaga["id"])
            return

        with OpenAI(timeout=30.0, max_retries=0) as cliente:
            resposta = cliente.embeddings.create(
                model=MODELO,
                input=texto,
                dimensions=1536,
                encoding_format="float"
            )

        vetor = resposta.data[0].embedding

        if len(vetor) != 1536:
            raise ValueError("Dimensão inesperada na resposta")

        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO public.vagas_embeddings (
                        vaga_id, variacao, modelo, embedding, texto_hash, tokens)
                    VALUES (%s, %s, %s, %s::vector, %s, %s)
                    ON CONFLICT (vaga_id, variacao, modelo)
                    DO UPDATE SET
                        embedding = EXCLUDED.embedding,
                        texto_hash = EXCLUDED.texto_hash,
                        tokens = EXCLUDED.tokens,
                        atualizado_em = NOW()
                    """, (
                        vaga["id"],
                        VARIACAO,
                        MODELO,
                        json.dumps(vetor),
                        texto_hash,
                        resposta.usage.prompt_tokens
                    )
                )

        print("Embedding salvo:", vaga["id"])
        print("Tokens usados:", resposta.usage.prompt_tokens)


if __name__ == "__main__":
    main()
