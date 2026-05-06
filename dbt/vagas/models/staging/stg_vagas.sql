with source as (
    select * from {{ source('public', 'vagas_raw') }}
),

cleaned as (
    select
        id,
        -- Padroniza o nome do cargo para titulo case e remove espaços extras
        initcap(trim(nome)) as cargo,

        -- Padroniza empresa
        initcap(trim(empresa)) as empresa,

        -- Padroniza cidade e estado
        nullif(initcap(trim(cidade)), '') as cidade,
        nullif(initcap(trim(estado)), '') as estado,

        -- Classifica senioridade com base no titulo da vaga
        case
            when lower(nome) like '%júnior%' or lower(nome) like '%junior%'
                or lower(nome) like '% jr%'   or lower(nome) like '%jr.%'
                or nome ~ '\sI(\s|$|-)'                                        then 'Júnior'
            when lower(nome) like '%pleno%' or lower(nome) like '%mid%'
                or lower(nome) like '% pl%'   or lower(nome) like '% pl/%'
                or nome ~ '\sII(\s|$|-)'                                       then 'Pleno'
            when lower(nome) like '%sênior%' or lower(nome) like '%senior%'
                or lower(nome) like '% sr%'   or lower(nome) like '% sr.%'
                or lower(nome) like '%pl/sr%'
                or nome ~ '\sIII(\s|$|-)'                                      then 'Sênior'
            when lower(nome) like '%estágio%' or lower(nome) like '%estagio%'
                or lower(nome) like '%intern%' or lower(nome) like '%estag%'   then 'Estágio'
            when lower(nome) like '%lead%' or lower(nome) like '%staff%'
                or lower(nome) like '%principal%' or lower(nome) like '%head%' then 'Especialista'
            else 'Não especificado'
        end as senioridade,

        -- Classifica o regime de trabalho
        case
            when lower(nome) like '%remoto%' or lower(nome) like '%remote%' or lower(regime) like '%remote%' then 'Remoto'
            when lower(nome) like '%híbrido%' or lower(nome) like '%hibrido%' or lower(regime) like '%hybrid%' then 'Híbrido'
            when lower(regime) like '%on_site%' or lower(regime) like '%presencial%' then 'Presencial'
            else 'Não especificado'
        end as regime_trabalho,

        fonte,
        coletado_em::date as data_coleta

    from source
    where id is not null
        and nome is not null
)

select * from cleaned