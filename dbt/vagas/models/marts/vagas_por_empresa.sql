with base as (
    select * from {{ ref('stg_vagas') }}
    where empresa is not null
)

select
    empresa,
    count(*)         as total_vagas,
    fonte,
    min(data_coleta) as primeira_coleta
from base
group by empresa, fonte
order by total_vagas desc
limit 20