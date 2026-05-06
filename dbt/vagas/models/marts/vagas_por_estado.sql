with base as (
    select * from {{ ref('stg_vagas') }}
    where estado is not null
)

select
    estado,
    count(*)                                            as total_vagas,
    count(*) filter (where fonte = 'linkedin')          as vagas_linkedin,
    count(*) filter (where fonte = 'gupy')              as vagas_gupy
from base
group by estado
order by total_vagas desc