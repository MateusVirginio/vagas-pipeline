import os
from contextlib import closing

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor

import json
from psycopg2.extras import execute_values

from src.embedding_batches import montar_lotes
from src.embedding_text import (
    calcular_hash,
    preparar_texto,
    validar_texto,
)

import logging
import time

import argparse
from openai import OpenAI


logger = logging.getLogger(__name__)
PRECO_USD_POR_MILHAO = 0.02

MODELO = "text-embedding-3-small"
VARIACAO = "titulo_empresa_descricao"


def carregar_pendencias(conn, modelo, variacao):
    with conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    v.id,
                    v.nome,
                    v.empresa,
                    v.descricao,
                    e.texto_hash AS hash_salvo
                FROM public.vagas_raw AS v
                LEFT JOIN public.vagas_embeddings AS e
                    ON e.vaga_id = v.id
                    AND e.variacao = %s
                    AND e.modelo = %s
                WHERE v.ultima_coleta >= NOW() - INTERVAL '60 days'
                ORDER BY v.id
            """, (variacao, modelo))
            vagas = cur.fetchall()

    pendencias = []
    atualizadas = 0
    invalidas = 0

    for vaga in vagas:
        try:
            texto = preparar_texto(vaga, variacao)
            tokens = validar_texto(texto)
        except ValueError as erro:
            invalidas += 1
            print(f"Entrada inválida: {vaga['id']} | {erro}")
            continue

        texto_hash = calcular_hash(texto)

        if vaga["hash_salvo"] == texto_hash:
            atualizadas += 1
            continue

        pendencias.append({
            "vaga_id": vaga["id"],
            "texto": texto,
            "texto_hash": texto_hash,
            "tokens": tokens,
        })

    print("Elegíveis:", len(vagas))
    print("Já atualizadas:", atualizadas)
    print("Inválidas:", invalidas)

    return pendencias

def gerar_lote(cliente, lote, modelo):
    if not lote:
        raise ValueError("O lote não pode estar vazio.")

    resposta = cliente.embeddings.create(
        model=modelo,
        input=[item["texto"] for item in lote],
        dimensions=1536,
        encoding_format="float",
    )

    indices = sorted(resultado.index for resultado in resposta.data)

    if indices != list(range(len(lote))):
        raise ValueError("A resposta não corresponde às entradas do lote.")

    registros = []

    for resultado in resposta.data:
        item = lote[resultado.index]

        if len(resultado.embedding) != 1536:
            raise ValueError(
                f"Dimensão inesperada para a vaga {item['vaga_id']}."
            )

        registros.append({
            **item,
            "embedding": resultado.embedding,
        })

    return registros, resposta.usage.prompt_tokens

def salvar_lote(conn, registros, modelo, variacao):
    if not registros:
        return 0

    linhas = [
        (
            item["vaga_id"],
            variacao,
            modelo,
            json.dumps(item["embedding"]),
            item["texto_hash"],
            item["tokens"],
        )
        for item in registros
    ]

    with conn:
        with conn.cursor() as cur:
            execute_values(
                cur,
                """
                INSERT INTO public.vagas_embeddings (
                    vaga_id, variacao, modelo, embedding,
                    texto_hash, tokens
                )
                VALUES %s
                ON CONFLICT (vaga_id, variacao, modelo)
                DO UPDATE SET
                    embedding = EXCLUDED.embedding,
                    texto_hash = EXCLUDED.texto_hash,
                    tokens = EXCLUDED.tokens,
                    atualizado_em = NOW()
                """,
                linhas,
                template="(%s, %s, %s, %s::vector, %s, %s)",
            )

    return len(linhas)

def processar_lote(cliente, conn, lote, modelo, variacao):
    inicio = time.perf_counter()

    logger.info(
        "Gerando lote | vagas=%s | modelo=%s | variacao=%s",
        len(lote),
        modelo,
        variacao,
    )

    try:
        registros, tokens = gerar_lote(cliente, lote, modelo)
    except Exception as erro:
        logger.error(
            "Falha na geração | tipo=%s",
            type(erro).__name__,
        )
        raise

    segundos_api = time.perf_counter() - inicio
    custo_estimado = tokens / 1_000_000 * PRECO_USD_POR_MILHAO

    logger.info(
        "Geração concluída | tokens=%s | custo_estimado_usd=%.8f"
        " | segundos_api=%.2f",
        tokens,
        custo_estimado,
        segundos_api,
    )

    try:
        quantidade = salvar_lote(conn, registros, modelo, variacao)
    except psycopg2.Error as erro:
        logger.error(
            "Falha na persistência após geração"
            " | tipo=%s | registros=%s",
            type(erro).__name__,
            len(registros),
        )
        raise

    logger.info(
        "Persistência confirmada | registros=%s | segundos_total=%.2f",
        quantidade,
        time.perf_counter() - inicio,
    )

    return quantidade



def main():
    parser = argparse.ArgumentParser(
        description="Diagnostica ou gera embeddings das vagas."
    )
    parser.add_argument("--executar", action="store_true")
    parser.add_argument("--max-lotes", type=int)
    parser.add_argument("--intervalo", type=int, default=60)
    parser.add_argument(
        "--variacao",
        choices=["titulo", "titulo_empresa_descricao"],
        default=VARIACAO,
    )
    args = parser.parse_args()

    if args.max_lotes is not None and args.max_lotes <= 0:
        parser.error("--max-lotes precisa ser positivo.")

    if args.intervalo < 0:
        parser.error("--intervalo não pode ser negativo.")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    load_dotenv(dotenv_path=".env", override=True)

    with closing(
        psycopg2.connect(os.environ["WAREHOUSE_DATABASE_URL"])
    ) as conn:
        pendencias = carregar_pendencias(conn, MODELO, args.variacao)
        lotes = list(montar_lotes(pendencias))

        print("Pendências totais:", len(pendencias))
        print("Lotes pendentes:", len(lotes))

        if args.max_lotes is not None:
            lotes = lotes[:args.max_lotes]

        tokens_selecionados = sum(
            item["tokens"]
            for lote in lotes
            for item in lote
        )
        custo_estimado = (
            tokens_selecionados / 1_000_000 * PRECO_USD_POR_MILHAO
        )

        print("Lotes selecionados:", len(lotes))
        print("Tokens selecionados:", tokens_selecionados)
        print(f"Custo estimado selecionado: US$ {custo_estimado:.8f}")

        if not args.executar:
            for numero, lote in enumerate(lotes, start=1):
                tokens = sum(item["tokens"] for item in lote)
                print(
                    f"Lote {numero}: {len(lote)} vagas | {tokens} tokens"
                )
            print("Diagnóstico concluído.")
            return

        if not lotes:
            print("Nenhuma pendência para executar.")
            return

        total_salvos = 0

        with OpenAI(timeout=60.0, max_retries=3) as cliente:
            for numero, lote in enumerate(lotes, start=1):
                if numero > 1:
                    logger.info("Aguardando %s segundos.", args.intervalo)
                    time.sleep(args.intervalo)

                logger.info("Processando lote %s/%s", numero, len(lotes))
                total_salvos += processar_lote(
                    cliente,
                    conn,
                    lote,
                    MODELO,
                    args.variacao,
                )

        logger.info(
            "Execução concluída | registros=%s | lotes=%s",
            total_salvos,
            len(lotes),
        )


if __name__ == "__main__":
    main()