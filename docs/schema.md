# Reporting star schema

```mermaid
erDiagram
    DIM_COUNTRY ||--o{ FACT_COUNTRY_DAY : identifies
    DIM_REPORT_DATE ||--o{ FACT_COUNTRY_DAY : dates

    DIM_COUNTRY {
        VARCHAR2 country_id PK
        VARCHAR2 country_name
        VARCHAR2 iso3
        NUMBER latitude
        NUMBER longitude
    }

    DIM_REPORT_DATE {
        DATE report_date PK
        DATE week_start
    }

    FACT_COUNTRY_DAY {
        VARCHAR2 country_id PK, FK
        DATE report_date PK, FK
        NUMBER cases_cumulative
        NUMBER deaths_cumulative
    }
```

The fact contains one row per JHU reporting location per date, including a row when one or both source observations are unavailable. A missing count is `NULL`. Latitude, longitude, and ISO alpha-3 codes are available where the geographic reference supports them. The calendar uses Monday as the first day of the reporting week.

`v_country_daily` derives signed daily changes and trailing seven-day means, and reconstructs cumulative values from the changes using window functions. Each first observed snapshot after a gap supplies a new cumulative baseline. `v_country_weekly` rolls daily changes up by location and week and includes the number of available case and death changes. The Python pipeline exports the same metrics for Power BI and the browser dashboard.
