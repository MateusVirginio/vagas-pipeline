CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS public.vagas_embeddings (
    vaga_id VARCHAR(100) NOT NULL
        REFERENCES public.vagas_raw(id) ON DELETE CASCADE,

    variacao TEXT NOT NULL
        CHECK (
            variacao IN (
                'titulo',
                'titulo_empresa_descricao'
            )
        ),

    modelo TEXT NOT NULL,
    embedding VECTOR(1536) NOT NULL,

    texto_hash TEXT NOT NULL
        CHECK (texto_hash ~ '^[0-9a-f]{64}$'),

    tokens INTEGER NOT NULL
        CHECK (tokens BETWEEN 1 AND 8000),

    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    PRIMARY KEY (vaga_id, variacao, modelo)
);