with base as (
    select * from {{ ref('stg_vagas') }}
    where empresa is not null
)

select
    empresa,
    count(*)         as total_vagas,
    min(data_coleta) as primeira_coleta
from base
group by empresa
order by total_vagas desc
limit 20
