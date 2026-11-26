-- Run after refreshing the covid_analytics schema. Set the session schema as needed.

-- Compare the latest full week with seven available daily deltas per metric.
SELECT c.country_name, w.week_start, w.cases_weekly, w.deaths_weekly
FROM v_country_weekly w
JOIN dim_country c ON c.country_id = w.country_id
WHERE w.week_start = (
    SELECT MAX(week_start) FROM v_country_weekly WHERE days_in_scope = 7
)
AND w.cases_observed_days = 7
AND w.deaths_observed_days = 7
ORDER BY w.cases_weekly DESC, c.country_name
FETCH FIRST 10 ROWS ONLY;

-- Show the signed daily flow, rolling mean, and recomputed cumulative count.
SELECT c.country_name, d.report_date, d.cases_daily, d.cases_avg_7d, d.cases_cumulative
FROM v_country_daily d
JOIN dim_country c ON c.country_id = d.country_id
WHERE c.country_id IN ('india', 'us', 'brazil')
AND d.report_date BETWEEN DATE '2023-02-24' AND DATE '2023-03-09'
ORDER BY d.report_date, c.country_name;

-- Count negative reported revisions and unavailable source observations by location.
SELECT
    c.country_name,
    COUNT(CASE WHEN d.cases_daily < 0 THEN 1 END) AS negative_case_days,
    COUNT(CASE WHEN d.deaths_daily < 0 THEN 1 END) AS negative_death_days,
    SUM(d.cases_missing) AS missing_case_snapshots,
    SUM(d.deaths_missing) AS missing_death_snapshots
FROM v_country_daily d
JOIN dim_country c ON c.country_id = d.country_id
GROUP BY c.country_name
ORDER BY negative_case_days DESC, negative_death_days DESC, c.country_name;
