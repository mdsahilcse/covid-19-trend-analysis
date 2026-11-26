DECLARE
    country_count PLS_INTEGER;
    date_count PLS_INTEGER;
    calendar_span PLS_INTEGER;
    daily_count PLS_INTEGER;
    expected_daily_count PLS_INTEGER;
    weekly_count PLS_INTEGER;
    expected_weekly_count PLS_INTEGER;
    differing_rows PLS_INTEGER;
    database_version VARCHAR2(200);
BEGIN
    SELECT COUNT(*) INTO country_count FROM dim_country;
    SELECT COUNT(*), MAX(report_date) - MIN(report_date) + 1
        INTO date_count, calendar_span FROM dim_report_date;
    SELECT COUNT(*) INTO daily_count FROM fact_country_day;

    IF country_count = 0 OR date_count = 0 OR date_count <> calendar_span
       OR daily_count <> country_count * date_count THEN
        RAISE_APPLICATION_ERROR(-20001, 'The country-day grid is empty or incomplete.');
    END IF;

    SELECT COUNT(*) INTO expected_daily_count FROM ext_daily;
    SELECT COUNT(*) INTO differing_rows FROM (
        SELECT * FROM v_country_daily
        MINUS
        SELECT * FROM ext_daily
    );

    IF differing_rows <> 0 OR daily_count <> expected_daily_count THEN
        RAISE_APPLICATION_ERROR(-20002, 'Oracle daily metrics differ from the Python export.');
    END IF;

    SELECT COUNT(*) INTO weekly_count FROM v_country_weekly;
    SELECT COUNT(*) INTO expected_weekly_count FROM ext_weekly;
    SELECT COUNT(*) INTO differing_rows FROM (
        SELECT * FROM v_country_weekly
        MINUS
        SELECT * FROM ext_weekly
    );

    IF differing_rows <> 0 OR weekly_count <> expected_weekly_count THEN
        RAISE_APPLICATION_ERROR(-20003, 'Oracle weekly metrics differ from the Python export.');
    END IF;

    SELECT version_full INTO database_version FROM v$instance;
    DBMS_OUTPUT.PUT_LINE('Oracle Database Free ' || database_version);
    DBMS_OUTPUT.PUT_LINE('Verified ' || country_count || ' reporting locations across '
        || date_count || ' reporting days.');
    DBMS_OUTPUT.PUT_LINE('Matched ' || daily_count || ' daily and ' || weekly_count
        || ' weekly rows against Python.');
END;
/
