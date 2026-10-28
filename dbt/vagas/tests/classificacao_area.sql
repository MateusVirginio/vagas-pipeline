-- Retorna apenas divergências: siglas não devem casar dentro de outras palavras.
with exemplos(titulo, esperado) as (
    values
        ('Machine Learning Engineer', 'Machine Learning'),
        ('Engenheira de Machine Learning e IA', 'Machine Learning'),
        ('Engenheiro de Aprendizado de Máquina', 'Machine Learning'),
        ('MLOps / Machine Learning Engineer', 'MLOps'),
        ('LLMOps Engineer', 'MLOps'),
        ('ML Ops Engineer', 'MLOps'),
        ('AI Engineering', 'Engenharia de IA'),
        ('Engenheiro de IA', 'Engenharia de IA'),
        ('Especialista em Inteligência Artificial', 'IA — outras funções'),
        ('Advogado de Governança de Inteligência Artificial', 'IA — outras funções'),
        ('Generative AI Engineer', 'Engenharia de IA'),
        ('GenAI Developer', 'Engenharia de IA'),
        ('LLM Engineer', 'Engenharia de IA'),
        ('Analista de Dados', 'Dados'),
        ('Data Scientist', 'Dados'),
        ('Analytics Engineer', 'Dados'),
        ('Engenharia de Software', 'Outras áreas'),
        ('Analista Financeiro', 'Outras áreas'),
        ('Assistente de Auditoria', 'Outras áreas')
), classificados as (
    select titulo, esperado, {{ classificar_area('titulo') }} as area
    from exemplos
)
select * from classificados where area <> esperado
