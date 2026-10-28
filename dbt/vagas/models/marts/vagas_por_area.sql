select
    area,
    count(*) as total_vagas
from {{ ref('stg_vagas') }}
group by area
order by total_vagas desc
