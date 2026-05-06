with base as (
    select * from {{ ref('stg_vagas') }}
)

select
    senioridade,
    count(*)                                                    as total_vagas,
    round(count(*) * 100.0 / sum(count(*)) over (), 1)          as percentual
from base
group by senioridade
order by total_vagas desc