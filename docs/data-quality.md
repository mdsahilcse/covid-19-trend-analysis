# Data quality report

The archive covers 2020-01-22 through 2023-03-09. It contains 229,743 daily observations across 201 reporting locations and 1,143 dates.

| Measure | Confirmed cases | Deaths |
|---|---:|---:|
| Final cumulative time series | 676,570,149 | 6,881,802 |
| Final independent daily report | 676,570,149 | 6,881,804 |
| Difference, daily report minus time series | 0 | 2 |
| Missing source component cells | 0 | 0 |
| Missing country cumulative dates | 0 | 0 |
| Unknown daily changes | 0 | 0 |
| Negative daily changes | 171 | 199 |
| Net count from negative changes | -851,329 | -7,679 |
| Positive changes after at least seven flat dates | 1,457 | 2,334 |
| Complete trailing-average windows | 228,537 | 228,537 |
| Sum of signed daily changes | 676,570,149 | 6,881,802 |
| Sum of signed weekly changes | 676,570,149 | 6,881,802 |

The published time series and daily report agree on case totals for every reporting location. The Netherlands is the sole final death discrepancy. The time series reports 23,705 deaths and the daily report shows 23,707. This analysis uses the cumulative time series consistently for daily, weekly and cumulative views.

Reporting locations without map coordinates are Diamond Princess, MS Zaandam. Locations without a geography code are Diamond Princess, MS Zaandam, Summer Olympics 2020, Winter Olympics 2022.

## Measurement rules

- Daily counts are changes between consecutive published cumulative totals. The first date uses a zero opening balance and can include earlier activity.
- Negative changes are retained as source revisions. Corrections can reflect deduplication or reclassification.
- Missing component observations make the country cumulative value unknown. Daily changes require adjacent cumulative observations and stay blank across a gap. Published zeros and flat series remain observed values.
- Weeks start Monday. Totals sum known daily changes and are blank where none are known. Coverage distinguishes missing increments from the two partial weeks at the archive edges.
- Trailing averages require seven consecutive known daily changes.
- A positive change after at least seven zero-change dates with a nonzero prior total flags a possible batch report. The inputs cannot identify the actual event date or delay.
- Locations use JHU country/group labels. Coordinates and ISO-like codes come from its location lookup. Country labels can include territories or special reporting groups.

## Sources

JHU CSSE COVID-19 Data at [archive revision `4360e50239b4eb6b22f3a1759323748f36752177`](https://github.com/CSSEGISandData/COVID-19/tree/4360e50239b4eb6b22f3a1759323748f36752177). Data licensed [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

The [independent daily report](https://github.com/CSSEGISandData/COVID-19/blob/4360e50239b4eb6b22f3a1759323748f36752177/csse_covid_19_data/csse_covid_19_daily_reports/03-09-2023.csv) covers 2023-03-09.

Dong E, Du H, Gardner L. An interactive web-based dashboard to track COVID-19 in real time. Lancet Infect Dis. 2020. [doi:10.1016/S1473-3099(20)30120-1](https://doi.org/10.1016/S1473-3099(20)30120-1).

| Pinned input | SHA-256 |
|---|---|
| [confirmed_global.csv](https://raw.githubusercontent.com/CSSEGISandData/COVID-19/4360e50239b4eb6b22f3a1759323748f36752177/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_confirmed_global.csv) | `e6234a59eec4359d2577358b5220e1a7e3da74c162913cdb7d882db1413f98c2` |
| [deaths_global.csv](https://raw.githubusercontent.com/CSSEGISandData/COVID-19/4360e50239b4eb6b22f3a1759323748f36752177/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_deaths_global.csv) | `4e87757a3e059c45650a1e1856614f8e339ee3c70653c378a7ba6f7b0ee8c72e` |
| [locations.csv](https://raw.githubusercontent.com/CSSEGISandData/COVID-19/4360e50239b4eb6b22f3a1759323748f36752177/csse_covid_19_data/UID_ISO_FIPS_LookUp_Table.csv) | `80bbd734ae7547dac8915d0960d01f43975c817bcddebebd19c026718a1368db` |
| [final_daily_report.csv](https://raw.githubusercontent.com/CSSEGISandData/COVID-19/4360e50239b4eb6b22f3a1759323748f36752177/csse_covid_19_data/csse_covid_19_daily_reports/03-09-2023.csv) | `6c7ca54bbad1482e03848ec0b03e7d733a35f9e0d2303478f61024c969ab5644` |
