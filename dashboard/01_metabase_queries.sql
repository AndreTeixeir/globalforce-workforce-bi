/*
=============================================================
GlobalForce · Workforce Management | BI
Queries SQL para Metabase (VERSÃO ALIAS-FREE PARA FILTROS)
=============================================================
Instruções: Use "Field Filter" para as 3 variáveis:
{{region}} -> dim_regiao.region_name
{{client}} -> dim_cliente.client_name
{{date}}   -> dim_data.period
*/

-- 1. KPI: Turnover Mensal (%)
SELECT 
    dim_data.period,
    (SUM(fato_workforce.is_terminated) * 100.0 / COUNT(fato_workforce.employee_id)) as turnover_pct
FROM fato_workforce
JOIN dim_data ON fato_workforce.date_id = dim_data.date_id
JOIN dim_regiao ON fato_workforce.region_id = dim_regiao.region_id
JOIN dim_cliente ON fato_workforce.assignment_id = dim_cliente.assignment_id
WHERE 1=1
  [[AND {{region}}]]
  [[AND {{client}}]]
  [[AND {{date}}]]
GROUP BY dim_data.period
ORDER BY dim_data.period;


-- 2. KPI: Utilização de Capacidade (%)
SELECT 
    dim_data.period,
    (SUM(fato_workforce.worked_hours) * 100.0 / SUM(fato_workforce.planned_hours)) as utilization_pct
FROM fato_workforce
JOIN dim_data ON fato_workforce.date_id = dim_data.date_id
JOIN dim_regiao ON fato_workforce.region_id = dim_regiao.region_id
JOIN dim_cliente ON fato_workforce.assignment_id = dim_cliente.assignment_id
WHERE 1=1
  [[AND {{region}}]]
  [[AND {{client}}]]
  [[AND {{date}}]]
GROUP BY dim_data.period
ORDER BY dim_data.period;


-- 3. KPI: Custo Total por Região (USD) - CORRIGIDA
SELECT 
    dim_regiao.region_name,
    SUM(fato_workforce.monthly_cost) as total_cost_usd
FROM fato_workforce
JOIN dim_regiao ON fato_workforce.region_id = dim_regiao.region_id
JOIN dim_data ON fato_workforce.date_id = dim_data.date_id -- Adicionado este JOIN
WHERE 1=1
  [[AND {{region}}]]
  [[AND {{client}}]]
  [[AND {{date}}]]
GROUP BY dim_regiao.region_name
ORDER BY total_cost_usd DESC;


-- 4. KPI: Atingimento de Metas por Cliente (%) - CORRIGIDA
SELECT 
    dim_cliente.client_name,
    AVG(fato_workforce.goal_achievement) as avg_goal_pct
FROM fato_workforce
JOIN dim_cliente ON fato_workforce.assignment_id = dim_cliente.assignment_id
JOIN dim_data ON fato_workforce.date_id = dim_data.date_id -- Adicionado este JOIN
WHERE 1=1
  [[AND {{region}}]]
  [[AND {{client}}]]
  [[AND {{date}}]]
GROUP BY dim_cliente.client_name
ORDER BY avg_goal_pct DESC;