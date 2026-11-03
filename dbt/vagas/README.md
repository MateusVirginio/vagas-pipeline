# Transformações dbt — Vagas Pipeline

Este projeto transforma as vagas coletadas da Gupy em modelos para o dashboard.
A coleta Python cria e atualiza `public.vagas_raw`; o dbt lê essa fonte e cria
as relações de staging e marts no schema `public`.

```text
public.vagas_raw
       ↓
   stg_vagas
       ├── vagas_por_area
       ├── vagas_por_estado
       ├── vagas_por_empresa
       └── vagas_por_senioridade
```

## Modelos

| Modelo | Responsabilidade |
|---|---|
| `stg_vagas` | Padroniza cargo, empresa e localização; classifica senioridade, regime e área; expõe a primeira inclusão e `ultima_coleta` |
| `vagas_por_area` | Conta vagas por área de atuação |
| `vagas_por_estado` | Conta vagas com estado informado |
| `vagas_por_empresa` | Lista as 20 empresas com mais vagas e a primeira data de coleta |
| `vagas_por_senioridade` | Conta vagas por senioridade e calcula os percentuais |

A macro `macros/classificar_area.sql` classifica o título, priorizando MLOps,
Machine Learning, IA e Dados. É uma heurística; não analisa a descrição.
Os modelos usam a materialização padrão de views do dbt.

## Executar

Na raiz do repositório, instale as dependências com `uv sync --locked` e configure
`WAREHOUSE_DATABASE_URL` no `.env`, conforme o [README principal](../../README.md).
Depois execute:

```bash
uv run python src/collect.py
uv run python src/run_dbt.py
```

O wrapper `run_dbt.py` carrega a URL e fornece ao perfil as variáveis `PGHOST`,
`PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE` e `PGSSLMODE`, sem gravar credenciais
no `profiles.yml`. Por padrão, o perfil usa SSL obrigatório; para o Postgres local,
informe `sslmode=disable` na URL.

## Testar

Com as variáveis `PG*` configuradas no ambiente, execute da raiz:

```bash
uv run dbt test --project-dir dbt/vagas --profiles-dir dbt/vagas
```

As variáveis exportadas pelo wrapper existem apenas no subprocesso de `dbt run`;
para executar `dbt test` diretamente, elas precisam estar definidas no terminal.
O teste singular `tests/classificacao_area.sql` retorna divergências entre
títulos de exemplo e a classificação esperada; zero linhas significa sucesso.

O `.gitignore` deste diretório exclui `target/`, `dbt_packages/` e logs gerados.
As pastas `analyses/`, `seeds/` e `snapshots/` são reservadas para futuras extensões.

## Relação com embeddings

`vagas_embeddings` é criada pelo SQL em `sql/` e preenchida pelos scripts Python.
Ela não é um modelo dbt. O workflow executa coleta, dbt, geração incremental de
embeddings e limpeza, nessa ordem. A busca semântica ainda está em desenvolvimento.
