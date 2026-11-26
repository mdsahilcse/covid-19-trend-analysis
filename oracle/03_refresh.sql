WHENEVER OSERROR EXIT FAILURE ROLLBACK
WHENEVER SQLERROR EXIT FAILURE ROLLBACK
SET FEEDBACK OFF
SET DEFINE OFF

ALTER SESSION SET CONTAINER = FREEPDB1;
ALTER SESSION SET CURRENT_SCHEMA = covid_analytics;
ALTER SESSION SET NLS_NUMERIC_CHARACTERS = '.,';
SET SERVEROUTPUT ON

-- Full refresh is a single transaction, including the cross-engine assertions.
LOCK TABLE dim_country, dim_report_date, fact_country_day IN EXCLUSIVE MODE;

DELETE FROM fact_country_day;
DELETE FROM dim_report_date;
DELETE FROM dim_country;

INSERT INTO dim_country (country_id, country_name, iso3, latitude, longitude)
SELECT country_id, country_name, iso3, latitude, longitude
FROM ext_countries;

INSERT INTO dim_report_date (report_date, week_start)
SELECT report_date, week_start
FROM ext_dates;

INSERT INTO fact_country_day (report_date, country_id, cases_cumulative, deaths_cumulative)
SELECT report_date, country_id, cases_cumulative, deaths_cumulative
FROM ext_daily;

@@04_verify.sql

COMMIT;
PROMPT Oracle refresh committed.
EXIT SUCCESS
