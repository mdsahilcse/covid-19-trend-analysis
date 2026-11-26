CREATE VIEW v_country_daily AS
WITH previous_observation AS (
    SELECT
        f.*,
        LAG(report_date) OVER (PARTITION BY country_id ORDER BY report_date) AS prior_date,
        LAG(cases_cumulative, 1, 0) OVER (
            PARTITION BY country_id ORDER BY report_date
        ) AS prior_cases,
        LAG(deaths_cumulative, 1, 0) OVER (
            PARTITION BY country_id ORDER BY report_date
        ) AS prior_deaths
    FROM fact_country_day f
),
daily_changes AS (
    SELECT
        country_id,
        report_date,
        cases_cumulative,
        deaths_cumulative,
        CASE WHEN prior_date IS NULL OR prior_date = report_date - 1
             THEN cases_cumulative - prior_cases END AS cases_daily,
        CASE WHEN prior_date IS NULL OR prior_date = report_date - 1
             THEN deaths_cumulative - prior_deaths END AS deaths_daily
    FROM previous_observation
),
baseline_segments AS (
    -- A known observation following a gap starts a new cumulative baseline.
    SELECT
        daily_changes.*,
        COUNT(CASE WHEN cases_daily IS NULL AND cases_cumulative IS NOT NULL THEN 1 END)
            OVER (PARTITION BY country_id ORDER BY report_date ROWS UNBOUNDED PRECEDING)
            AS cases_segment,
        COUNT(CASE WHEN deaths_daily IS NULL AND deaths_cumulative IS NOT NULL THEN 1 END)
            OVER (PARTITION BY country_id ORDER BY report_date ROWS UNBOUNDED PRECEDING)
            AS deaths_segment
    FROM daily_changes
)
SELECT
    report_date,
    country_id,
    cases_daily,
    deaths_daily,
    CASE WHEN cases_cumulative IS NOT NULL THEN
        SUM(COALESCE(cases_daily, cases_cumulative)) OVER (
            PARTITION BY country_id, cases_segment
            ORDER BY report_date ROWS UNBOUNDED PRECEDING
        ) END AS cases_cumulative,
    CASE WHEN deaths_cumulative IS NOT NULL THEN
        SUM(COALESCE(deaths_daily, deaths_cumulative)) OVER (
            PARTITION BY country_id, deaths_segment
            ORDER BY report_date ROWS UNBOUNDED PRECEDING
        ) END AS deaths_cumulative,
    CASE WHEN COUNT(cases_daily) OVER (
            PARTITION BY country_id ORDER BY report_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
        ) = 7 THEN ROUND(AVG(cases_daily) OVER (
            PARTITION BY country_id ORDER BY report_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
        ), 6) END AS cases_avg_7d,
    CASE WHEN COUNT(deaths_daily) OVER (
            PARTITION BY country_id ORDER BY report_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
        ) = 7 THEN ROUND(AVG(deaths_daily) OVER (
            PARTITION BY country_id ORDER BY report_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
        ), 6) END AS deaths_avg_7d,
    CASE WHEN cases_cumulative IS NULL THEN 1 ELSE 0 END AS cases_missing,
    CASE WHEN deaths_cumulative IS NULL THEN 1 ELSE 0 END AS deaths_missing
FROM baseline_segments;

CREATE VIEW v_country_weekly AS
SELECT
    d.week_start,
    k.country_id,
    SUM(k.cases_daily) AS cases_weekly,
    SUM(k.deaths_daily) AS deaths_weekly,
    COUNT(k.cases_daily) AS cases_observed_days,
    COUNT(k.deaths_daily) AS deaths_observed_days,
    COUNT(*) AS days_in_scope
FROM v_country_daily k
JOIN dim_report_date d ON d.report_date = k.report_date
GROUP BY d.week_start, k.country_id;
