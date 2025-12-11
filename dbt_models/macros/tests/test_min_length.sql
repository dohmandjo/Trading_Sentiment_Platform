{% test min_length(model, column_name, min_value) %}

SELECT
    *
FROM {{ model }}
WHERE LENGTH(trim({{ column_name }})) <= {{ min_value }}

{% endtest %}
