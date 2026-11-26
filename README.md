# COVID-19 Trend Analysis

Explore historical COVID-19 reporting from **22 January 2020 to 9 March 2023**. The project turns a frozen Johns Hopkins CSSE archive into reproducible daily, weekly, and cumulative trends. It includes a Python pipeline, an Oracle star schema and analytic views, a Power BI project, and an interactive browser dashboard.

| Reporting locations | Daily rows | Final reported cases | Final reported deaths |
| ---: | ---: | ---: | ---: |
| 201 | 229,743 | 676,570,149 | 6,881,802 |

The cases match the publisher's final daily snapshot at every location. The final daily snapshot lists two more deaths in the Netherlands than the historical time series. The analysis keeps the time-series value and documents the difference.

## Build and open the dashboard

Requires Python 3.9 or newer. The pipeline and the browser dashboard use standard libraries. The first build downloads the pinned public inputs.

```sh
git clone https://github.com/mdsahilcse/covid-19-trend-analysis.git
cd covid-19-trend-analysis
python3 -m src.pipeline --out data/processed
python3 -m unittest discover -s tests -v
python3 -m http.server 8000 --bind 127.0.0.1
```

Open the local dashboard to select countries, choose a period and reporting metric, and switch between daily, weekly, and cumulative views. Select a point in the weekly chart to inspect that week's daily reports. The map shades locations by their cumulative counts at the selected end date. [Local dashboard](http://127.0.0.1:8000/dashboard/)

## Oracle and Power BI

- **Oracle.** The star schema stores the reporting geography and date dimensions, along with one fact per location and day. The SQL rebuilds the daily change, seven-day average, weekly totals, and cumulative sums using Oracle analytic functions. [Oracle instructions](oracle/README.md) · [Schema diagram](docs/schema.md)
- **Power BI.** The editable Power BI project includes a semantic model and report definition. Follow its setup instructions in Windows Power BI Desktop to refresh the local data and save a `.pbix` file. The source project is included. Desktop rendering and export require Windows. [Power BI instructions](power-bi/README.md)

## Analysis materials

- Project prompt and acceptance criteria. [Build prompt](docs/project-prompt.txt)
- Problem statement, metrics, methodology, and dataset attribution. [Methodology](docs/methodology.md)
- Peak timing, final country totals, and large source revisions. [Insights](docs/insights.md)
- Source checksums, final snapshot reconciliation, and correction counts. [Data-quality report](docs/data-quality.md)
- A short tour of country comparison, weekly drill-down, and the map. [Demo video](docs/covid-19-demo.mp4)

## Data and interpretation

The data comes from the **COVID-19 Data Repository by the Center for Systems Science and Engineering (CSSE) at Johns Hopkins University**, copyright Johns Hopkins University 2020, CC BY 4.0. The project pins the source at `4360e50239b4eb6b22f3a1759323748f36752177` and restructures it into daily and weekly records. Counts describe reports received by the source. Backlogs, changing practices, and negative corrections affect the series. [JHU CSSE COVID-19 Data](https://github.com/CSSEGISandData/COVID-19) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) · [Dong, Du, and Gardner, 2020](https://doi.org/10.1016/S1473-3099(20)30120-1)
