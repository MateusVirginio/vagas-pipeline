with base as (
    select * from {{ ref('stg_vagas') }}
    where estado is not null
)

select
    estado,
    count(*) as total_vagas
from base
group by estado
order by total_vagas desc
