# Problem statement and KPIs

This project compares the timing and scale of historical COVID-19 reporting across countries and other locations in the Johns Hopkins CSSE archive. The period begins on 22 January 2020 and ends on 9 March 2023, the final date in the selected series. The unit of analysis is one calendar date and one JHU reporting location. Some territories and exceptional groups appear as separate reporting locations.

| KPI | Definition |
| --- | --- |
| Daily reported cases or deaths | Change in the location's cumulative total from the previous calendar date. The first date uses a zero opening balance. A negative result represents a correction in the published series. |
| Weekly reported cases or deaths | Sum of the signed daily values in a Monday-start calendar week. An incomplete week carries a coverage count. The opening and closing weeks contain fewer than seven dates in scope. |
| Cumulative cases or deaths | Source total as of the selected date, after aggregating all of the location's source components. Cumulative values must be compared on the same date across locations. |
| Trailing seven-day average | Mean of seven consecutive daily values ending on the displayed date. The value is blank when the full window is unavailable. |
| Daily completeness | Count of location dates with a computable daily change, tracked independently for cases and deaths. |
| Source reconciliation | The difference between the location's last cumulative total and the publisher's separately released daily snapshot on the same date. |

The data records publication-day changes. A spike can reflect new reports, backlogs, changes in the definition of a reported case, or retrospective revisions. The archive supplies no consistent event-date series for distinguishing those effects, and the processing leaves large changes on their reported dates. Signed declines are retained in weekly sums and trailing averages. A blank source observation is kept as unknown. When either daily endpoint is unavailable, the daily change is also unknown.

The comparison uses absolute counts. Population, age, testing practice, and reporting coverage differ across locations. Case counts reflect reported records, and rankings should be read in that context. The browser map shades available boundaries by cumulative count. Power BI uses the source's representative coordinates.

## Source and attribution

The underlying historical data is the **COVID-19 Data Repository by the Center for Systems Science and Engineering (CSSE) at Johns Hopkins University**, copyright Johns Hopkins University 2020 and licensed under CC BY 4.0. This project restructures the data, aggregates source components, and derives additional metrics. [Repository and source attribution](https://github.com/CSSEGISandData/COVID-19) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)

The time series and final daily snapshot are pinned to revision `4360e50239b4eb6b22f3a1759323748f36752177`. [Pinned snapshot](https://github.com/CSSEGISandData/COVID-19/tree/4360e50239b4eb6b22f3a1759323748f36752177)

Dong E, Du H, Gardner L. An interactive web-based dashboard to track COVID-19 in real time. *Lancet Infectious Diseases*. 2020;20(5):533–534. [DOI](https://doi.org/10.1016/S1473-3099(20)30120-1)
