CREATE TABLE dim_country (
    country_id   VARCHAR2(80 CHAR) CONSTRAINT country_pk PRIMARY KEY,
    country_name VARCHAR2(160 CHAR) NOT NULL,
    iso3         VARCHAR2(3 CHAR),
    latitude     NUMBER,
    longitude    NUMBER,
    CONSTRAINT country_latitude_ck CHECK (latitude BETWEEN -90 AND 90),
    CONSTRAINT country_longitude_ck CHECK (longitude BETWEEN -180 AND 180)
);

CREATE TABLE dim_report_date (
    report_date DATE CONSTRAINT report_date_pk PRIMARY KEY,
    week_start  DATE NOT NULL,
    CONSTRAINT report_date_midnight_ck CHECK (report_date = TRUNC(report_date)),
    CONSTRAINT report_date_week_ck CHECK (week_start = TRUNC(report_date, 'IW'))
);

CREATE TABLE fact_country_day (
    country_id        VARCHAR2(80 CHAR) NOT NULL,
    report_date       DATE NOT NULL,
    cases_cumulative  NUMBER(18, 0),
    deaths_cumulative NUMBER(18, 0),
    CONSTRAINT country_day_pk PRIMARY KEY (country_id, report_date),
    CONSTRAINT country_day_country_fk FOREIGN KEY (country_id)
        REFERENCES dim_country (country_id),
    CONSTRAINT country_day_date_fk FOREIGN KEY (report_date)
        REFERENCES dim_report_date (report_date),
    CONSTRAINT country_day_cases_ck CHECK (cases_cumulative >= 0),
    CONSTRAINT country_day_deaths_ck CHECK (deaths_cumulative >= 0)
);

CREATE INDEX country_day_report_date_ix ON fact_country_day (report_date);

CREATE TABLE ext_countries (
    country_id   VARCHAR2(80 CHAR),
    country_name VARCHAR2(160 CHAR),
    iso3         VARCHAR2(3 CHAR),
    latitude     NUMBER,
    longitude    NUMBER
) ORGANIZATION EXTERNAL (
    TYPE ORACLE_LOADER
    DEFAULT DIRECTORY covid_input
    ACCESS PARAMETERS (
        RECORDS DELIMITED BY NEWLINE CHARACTERSET AL32UTF8
        SKIP = 1 NOBADFILE NODISCARDFILE NOLOGFILE
        FIELDS CSV WITH EMBEDDED MISSING FIELD VALUES ARE NULL (
            country_id CHAR(80),
            country_name CHAR(640),
            iso3 CHAR(3),
            latitude DECIMAL EXTERNAL(40),
            longitude DECIMAL EXTERNAL(40)
        )
    )
    LOCATION ('countries.csv')
) REJECT LIMIT 0;

CREATE TABLE ext_dates (
    report_date DATE,
    week_start  DATE
) ORGANIZATION EXTERNAL (
    TYPE ORACLE_LOADER
    DEFAULT DIRECTORY covid_input
    ACCESS PARAMETERS (
        RECORDS DELIMITED BY NEWLINE CHARACTERSET AL32UTF8
        SKIP = 1 NOBADFILE NODISCARDFILE NOLOGFILE
        FIELDS CSV WITH EMBEDDED (
            report_date CHAR(10) DATE_FORMAT DATE MASK "YYYY-MM-DD",
            week_start CHAR(10) DATE_FORMAT DATE MASK "YYYY-MM-DD"
        )
    )
    LOCATION ('dates.csv')
) REJECT LIMIT 0;

CREATE TABLE ext_daily (
    report_date       DATE,
    country_id        VARCHAR2(80 CHAR),
    cases_daily       NUMBER,
    deaths_daily      NUMBER,
    cases_cumulative  NUMBER,
    deaths_cumulative NUMBER,
    cases_avg_7d      NUMBER,
    deaths_avg_7d     NUMBER,
    cases_missing     NUMBER,
    deaths_missing    NUMBER
) ORGANIZATION EXTERNAL (
    TYPE ORACLE_LOADER
    DEFAULT DIRECTORY covid_input
    ACCESS PARAMETERS (
        RECORDS DELIMITED BY NEWLINE CHARACTERSET AL32UTF8
        SKIP = 1 NOBADFILE NODISCARDFILE NOLOGFILE
        FIELDS CSV WITH EMBEDDED MISSING FIELD VALUES ARE NULL (
            report_date CHAR(10) DATE_FORMAT DATE MASK "YYYY-MM-DD",
            country_id CHAR(80),
            cases_daily INTEGER EXTERNAL(24),
            deaths_daily INTEGER EXTERNAL(24),
            cases_cumulative INTEGER EXTERNAL(24),
            deaths_cumulative INTEGER EXTERNAL(24),
            cases_avg_7d DECIMAL EXTERNAL(36),
            deaths_avg_7d DECIMAL EXTERNAL(36),
            cases_missing INTEGER EXTERNAL(1),
            deaths_missing INTEGER EXTERNAL(1)
        )
    )
    LOCATION ('daily.csv')
) REJECT LIMIT 0;

CREATE TABLE ext_weekly (
    week_start           DATE,
    country_id           VARCHAR2(80 CHAR),
    cases_weekly         NUMBER,
    deaths_weekly        NUMBER,
    cases_observed_days  NUMBER,
    deaths_observed_days NUMBER,
    days_in_scope        NUMBER
) ORGANIZATION EXTERNAL (
    TYPE ORACLE_LOADER
    DEFAULT DIRECTORY covid_input
    ACCESS PARAMETERS (
        RECORDS DELIMITED BY NEWLINE CHARACTERSET AL32UTF8
        SKIP = 1 NOBADFILE NODISCARDFILE NOLOGFILE
        FIELDS CSV WITH EMBEDDED MISSING FIELD VALUES ARE NULL (
            week_start CHAR(10) DATE_FORMAT DATE MASK "YYYY-MM-DD",
            country_id CHAR(80),
            cases_weekly INTEGER EXTERNAL(24),
            deaths_weekly INTEGER EXTERNAL(24),
            cases_observed_days INTEGER EXTERNAL(1),
            deaths_observed_days INTEGER EXTERNAL(1),
            days_in_scope INTEGER EXTERNAL(1)
        )
    )
    LOCATION ('weekly.csv')
) REJECT LIMIT 0;
