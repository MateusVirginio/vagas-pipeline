{% macro classificar_area(titulo) %}
-- A classificação usa o título, com limites de palavra para siglas como IA e AI.
-- A ordem prioriza operações de ML/LLM e ML antes das regras gerais de IA e dados.
case
    when lower({{ titulo }}) ~ '\m(ml[ -]?ops|llm[ -]?ops)\M'
        then 'MLOps'
    when lower({{ titulo }}) ~ '\m(machine[ -]learning|aprendizado de m[aá]quina|aprendizagem de m[aá]quina|deep[ -]learning|ml engineer|engenheir[oa] de ml)\M'
        then 'Machine Learning'
    when lower({{ titulo }}) ~ '\m(ia|ai|genai|llm|llms|intelig[eê]ncia artificial|artificial intelligence)\M'
        then case
            when lower({{ titulo }}) ~ '\m(engenheir[oa]|engenharia|engineer|engineering|desenvolvedor[a]?|developer|arquiteto|arquiteta|architect|tech lead)\M'
                then 'Engenharia de IA'
            else 'IA — outras funções'
        end
    when lower({{ titulo }}) ~ '\m(dados|data|analytics)\M'
        then 'Dados'
    else 'Outras áreas'
end
{% endmacro %}
