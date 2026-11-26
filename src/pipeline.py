"""Build the COVID-19 reporting tables from the archived JHU CSSE dataset."""

from __future__ import annotations

import argparse
from collections import Counter, deque
from concurrent.futures import ThreadPoolExecutor
import csv
from dataclasses import dataclass
from datetime import date, timedelta
from hashlib import sha256
from itertools import groupby
import json
from pathlib import Path
import re
from shutil import which
import subprocess
from tempfile import NamedTemporaryFile, TemporaryDirectory
from urllib.request import urlopen

REPO = "https://github.com/CSSEGISandData/COVID-19"
REVISION = "4360e50239b4eb6b22f3a1759323748f36752177"
RAW_URL = f"https://raw.githubusercontent.com/CSSEGISandData/COVID-19/{REVISION}/csse_covid_19_data"
SOURCES = {
    "confirmed_global.csv": (
        "csse_covid_19_time_series/time_series_covid19_confirmed_global.csv",
        "e6234a59eec4359d2577358b5220e1a7e3da74c162913cdb7d882db1413f98c2",
    ),
    "deaths_global.csv": (
        "csse_covid_19_time_series/time_series_covid19_deaths_global.csv",
        "4e87757a3e059c45650a1e1856614f8e339ee3c70653c378a7ba6f7b0ee8c72e",
    ),
    "locations.csv": (
        "UID_ISO_FIPS_LookUp_Table.csv",
        "80bbd734ae7547dac8915d0960d01f43975c817bcddebebd19c026718a1368db",
    ),
    "final_daily_report.csv": (
        "csse_covid_19_daily_reports/03-09-2023.csv",
        "6c7ca54bbad1482e03848ec0b03e7d733a35f9e0d2303478f61024c969ab5644",
    ),
}
FIRST_DATE = date(2020, 1, 22)
LAST_DATE = date(2023, 3, 9)
METRICS = ("cases", "deaths")
POLICIES = {
    "daily": (
        "Daily counts are changes between consecutive published cumulative totals. "
        "The first date uses a zero opening balance and can include earlier activity."
    ),
    "corrections": (
        "Negative changes are retained as source revisions. Corrections can reflect "
        "deduplication or reclassification."
    ),
    "gaps": (
        "Missing component observations make the country cumulative value unknown. "
        "Daily changes require adjacent cumulative observations and stay blank across "
        "a gap. Published zeros and flat series remain observed values."
    ),
    "weekly": (
        "Weeks start Monday. Totals sum known daily changes and are blank where none are known. "
        "Coverage distinguishes missing increments from the two partial weeks at the archive edges."
    ),
    "rolling": "Trailing averages require seven consecutive known daily changes.",
    "delays": (
        "A positive change after at least seven zero-change dates with a nonzero prior total "
        "flags a possible batch report. The inputs cannot identify the actual event date or delay."
    ),
    "geography": (
        "Locations use JHU country/group labels. Coordinates and ISO-like codes come from its "
        "location lookup. Country labels can include territories or special reporting groups."
    ),
}
COUNTRY_COLUMNS = ("country_id", "country_name", "iso3", "latitude", "longitude")
DATE_COLUMNS = ("report_date", "week_start")
DAILY_COLUMNS = (
    "report_date", "country_id", "cases_daily", "deaths_daily", "cases_cumulative",
    "deaths_cumulative", "cases_avg_7d", "deaths_avg_7d", "cases_missing", "deaths_missing",
)
WEEKLY_COLUMNS = (
    "week_start", "country_id", "cases_weekly", "deaths_weekly", "cases_observed_days",
    "deaths_observed_days", "days_in_scope",
)


@dataclass(frozen=True)
class Observation:
    cumulative: int | None
    daily: int | None
    avg_7d: str | None
    possible_batch_report: bool


def download(url: str) -> bytes:
    # curl can connect promptly on networks with unavailable IPv6 routes.
    curl = which("curl")
    if curl:
        response = subprocess.run(
            [
                curl, "--disable", "--fail", "--silent", "--show-error", "--location",
                "--connect-timeout", "8", "--max-time", "30", "--retry", "2",
                "--retry-delay", "1", url,
            ],
            capture_output=True,
        )
        if response.returncode:
            reason = response.stderr.decode("utf-8", errors="replace").strip()
            raise OSError(f"Could not download {url}: {reason}")
        return response.stdout
    with urlopen(url, timeout=10) as response:
        return response.read()


def ensure_source(raw_dir: Path, name: str, offline: bool) -> None:
    """Reuse or atomically replace an input only if its pinned checksum matches."""
    suffix, expected = SOURCES[name]
    destination = raw_dir / name
    if destination.is_file() and sha256(destination.read_bytes()).hexdigest() == expected:
        return
    if offline:
        raise ValueError(f"{destination} is missing or its checksum differs from the archived source")

    body = download(f"{RAW_URL}/{suffix}")
    if sha256(body).hexdigest() != expected:
        raise ValueError(f"Downloaded {name} does not match its archived SHA-256 checksum")
    pending_path = None
    try:
        with NamedTemporaryFile(dir=raw_dir, delete=False) as pending:
            pending_path = Path(pending.name)
            pending.write(body)
        pending_path.replace(destination)
    finally:
        if pending_path is not None:
            pending_path.unlink(missing_ok=True)


def calendar(first: date, last: date) -> list[date]:
    return [first + timedelta(days=offset) for offset in range((last - first).days + 1)]


def monday(report_date: date) -> date:
    return report_date - timedelta(days=report_date.weekday())


def country_id(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def load_time_series(path: Path, dates: list[date]) -> tuple[dict[str, list[int | None]], int]:
    """Aggregate every province row under its source country/group."""
    totals: dict[str, list[int | None]] = {}
    seen = set()
    missing_cells = 0
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.reader(stream)
        header = next(reader)
        if header[:4] != ["Province/State", "Country/Region", "Lat", "Long"]:
            raise ValueError(f"Unexpected time-series header in {path.name}")
        indexes = {}
        for index, column in enumerate(header[4:], start=4):
            month, day, year = map(int, column.split("/"))
            report_date = date(2000 + year, month, day)
            if report_date in indexes:
                raise ValueError(f"Duplicate date {report_date} in {path.name}")
            indexes[report_date] = index
        if not indexes or min(indexes) != dates[0] or max(indexes) != dates[-1]:
            raise ValueError(f"Unexpected archive date range in {path.name}")

        for row_number, row in enumerate(reader, start=2):
            if len(row) != len(header) or not row[1].strip():
                raise ValueError(f"Malformed row {row_number} in {path.name}")
            province, country = (value.strip() for value in row[:2])
            if (country, province) in seen:
                raise ValueError(f"Duplicate place {country}/{province} in {path.name}")
            seen.add((country, province))
            values = totals.setdefault(country, [0] * len(dates))
            for offset, report_date in enumerate(dates):
                index = indexes.get(report_date)
                source_value = row[index].strip() if index is not None else ""
                if not source_value:
                    values[offset] = None
                    missing_cells += 1
                    continue
                count = int(source_value)
                if count < 0:
                    raise ValueError(f"Negative cumulative value in {path.name} row {row_number}")
                previous_component_sum = values[offset]
                if previous_component_sum is not None:
                    values[offset] = previous_component_sum + count
    return totals, missing_cells


def load_geography(path: Path) -> dict[str, tuple[str, str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return {
            row["Country_Region"]: (row["iso3"], row["Lat"], row["Long_"])
            for row in csv.DictReader(stream)
            if not row["Province_State"] and not row["Admin2"]
        }


def load_snapshot(path: Path) -> dict[str, Counter]:
    """Parse the independent daily report at its original, finer source grain."""
    totals: dict[str, Counter] = {"cases": Counter(), "deaths": Counter()}
    seen = set()
    with path.open(newline="", encoding="utf-8-sig") as stream:
        for row in csv.DictReader(stream):
            country = row["Country_Region"]
            source_key = (country, row["Province_State"], row["Admin2"])
            if not country or source_key in seen:
                raise ValueError(f"Invalid or duplicate snapshot record {source_key}")
            seen.add(source_key)
            for metric, column in (("cases", "Confirmed"), ("deaths", "Deaths")):
                value = int(row[column])
                if value < 0:
                    raise ValueError(f"Negative {column} in snapshot for {source_key}")
                totals[metric][country] += value
    return totals


def derive(cumulative: list[int | None]) -> list[Observation]:
    previous = 0
    flat_days = 0
    window = deque(maxlen=7)
    result = []
    for count in cumulative:
        daily = count - previous if count is not None and previous is not None else None
        window.append(daily)
        average = None
        if len(window) == 7 and None not in window:
            average = f"{sum(window) / 7:.6f}"
        possible_batch_report = daily is not None and daily > 0 and flat_days >= 7
        result.append(Observation(count, daily, average, possible_batch_report))
        flat_days = flat_days + 1 if daily == 0 and count > 0 else 0
        previous = count
    return result


def create_csv(stream, columns):
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(columns)
    return writer


def write_dimensions(destination, dates, country_rows):
    with (destination / "dates.csv").open("w", encoding="utf-8", newline="") as stream:
        create_csv(stream, DATE_COLUMNS).writerows((day, monday(day)) for day in dates)
    with (destination / "countries.csv").open("w", encoding="utf-8", newline="") as stream:
        create_csv(stream, COUNTRY_COLUMNS).writerows(country_rows)


def measure(points: list[Observation]) -> Counter:
    known = [point.daily for point in points if point.daily is not None]
    negatives = [value for value in known if value < 0]
    return Counter({
        "missing_cumulative_days": sum(point.cumulative is None for point in points),
        "unknown_daily_increments": len(points) - len(known),
        "negative_daily_corrections": len(negatives),
        "negative_daily_total": sum(negatives),
        "complete_trailing_windows": sum(point.avg_7d is not None for point in points),
        "possible_batch_reports": sum(point.possible_batch_report for point in points),
        "daily_sum": sum(known),
    })


def write_facts(destination, dates, country_rows, cumulative_by_metric):
    stats = {metric: Counter() for metric in METRICS}
    weekly_count = 0
    with (
        (destination / "daily.csv").open("w", encoding="utf-8", newline="") as daily_file,
        (destination / "weekly.csv").open("w", encoding="utf-8", newline="") as weekly_file,
    ):
        daily, weekly = create_csv(daily_file, DAILY_COLUMNS), create_csv(weekly_file, WEEKLY_COLUMNS)
        for location, country, *_ in country_rows:
            series = [derive(cumulative_by_metric[metric][country]) for metric in METRICS]
            for report_date, cases, deaths in zip(dates, *series):
                daily.writerow((
                    report_date, location, cases.daily, deaths.daily, cases.cumulative,
                    deaths.cumulative, cases.avg_7d, deaths.avg_7d,
                    int(cases.cumulative is None), int(deaths.cumulative is None),
                ))
            for metric, series_points in zip(METRICS, series):
                stats[metric].update(measure(series_points))
            for week, days in groupby(zip(dates, *series), key=lambda row: monday(row[0])):
                rows = list(days)
                counts = [
                    [point.daily for point in points if point.daily is not None]
                    for points in zip(*(row[1:] for row in rows))
                ]
                sums = [sum(values) if values else None for values in counts]
                weekly.writerow((week, location, *sums, *(len(values) for values in counts), len(rows)))
                weekly_count += 1
                for metric, total in zip(METRICS, sums):
                    stats[metric]["weekly_sum"] += total if total is not None else 0
    return stats, weekly_count


def crosscheck(cumulative_by_metric, snapshot, stats):
    known_differences = {"cases": {}, "deaths": {"Netherlands": (23705, 23707)}}
    for metric in METRICS:
        latest = {country: values[-1] for country, values in cumulative_by_metric[metric].items()}
        published = snapshot[metric]
        if latest.keys() != published.keys() or None in latest.values():
            raise ValueError(f"Final {metric} observations lack complete snapshot coverage")
        differences = {
            country: (total, published[country])
            for country, total in latest.items()
            if total != published[country]
        }
        if differences != known_differences[metric]:
            raise ValueError(f"Unexpected final source differences for {metric}: {differences}")
        series_total, snapshot_total = sum(latest.values()), sum(published.values())
        summary = stats[metric]
        if summary["daily_sum"] != summary["weekly_sum"]:
            raise ValueError(f"Weekly and daily {metric} totals do not reconcile")
        if summary["unknown_daily_increments"] == 0 and summary["daily_sum"] != series_total:
            raise ValueError(f"Signed daily {metric} changes do not reconcile to the cumulative series")
        summary["time_series_total"] = series_total
        summary["snapshot_total"] = snapshot_total
        summary["difference_snapshot_minus_time_series"] = snapshot_total - series_total
        summary["snapshot_discrepancies"] = [
            {"country_name": country, "time_series": totals[0], "daily_report": totals[1]}
            for country, totals in differences.items()
        ]


def quality_markdown(quality):
    coverage, metrics = quality["coverage"], quality["metrics"]
    lines = [
        "# Data quality report",
        "",
        f"The archive covers {coverage['first_date']} through {coverage['last_date']}. "
        f"It contains {coverage['country_days']:,} daily observations across "
        f"{coverage['reporting_locations']} reporting locations and {coverage['dates']:,} dates.",
        "",
        "| Measure | Confirmed cases | Deaths |",
        "|---|---:|---:|",
    ]
    for label, key in (
        ("Final cumulative time series", "time_series_total"),
        ("Final independent daily report", "snapshot_total"),
        ("Difference, daily report minus time series", "difference_snapshot_minus_time_series"),
        ("Missing source component cells", "source_component_missing_cells"),
        ("Missing country cumulative dates", "missing_cumulative_days"),
        ("Unknown daily changes", "unknown_daily_increments"),
        ("Negative daily changes", "negative_daily_corrections"),
        ("Net count from negative changes", "negative_daily_total"),
        ("Positive changes after at least seven flat dates", "possible_batch_reports"),
        ("Complete trailing-average windows", "complete_trailing_windows"),
        ("Sum of signed daily changes", "daily_sum"),
        ("Sum of signed weekly changes", "weekly_sum"),
    ):
        lines.append(f"| {label} | {metrics['cases'][key]:,} | {metrics['deaths'][key]:,} |")
    lines.extend([
        "",
        "The published time series and daily report agree on case totals for every reporting location. "
        "The Netherlands is the sole final death discrepancy. "
        "The time series reports 23,705 deaths and the daily report shows 23,707. "
        "This analysis uses the cumulative time series consistently for daily, weekly and cumulative views.",
        "",
        f"Reporting locations without map coordinates are {', '.join(coverage['map_coordinates_missing'])}. "
        f"Locations without a geography code are {', '.join(coverage['iso3_missing'])}.",
        "",
        "## Measurement rules",
        "",
        *(f"- {policy}" for policy in POLICIES.values()),
        "",
        "## Sources",
        "",
        f"JHU CSSE COVID-19 Data at [archive revision `{REVISION}`]({REPO}/tree/{REVISION}). "
        "Data licensed [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).",
        "",
        f"The [independent daily report]({REPO}/blob/{REVISION}/csse_covid_19_data/"
        f"{SOURCES['final_daily_report.csv'][0]}) covers 2023-03-09.",
        "",
        "Dong E, Du H, Gardner L. An interactive web-based dashboard to track COVID-19 in real time. "
        "Lancet Infect Dis. 2020. [doi:10.1016/S1473-3099(20)30120-1]"
        "(https://doi.org/10.1016/S1473-3099(20)30120-1).",
        "",
        "| Pinned input | SHA-256 |",
        "|---|---|",
        *(
            f"| [{name}]({details['url']}) | `{details['sha256']}` |"
            for name, details in quality["source"]["sources"].items()
        ),
    ])
    return "\n".join(lines) + "\n"


def build(raw_dir: Path, out_dir: Path, offline: bool = False):
    raw_dir.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=len(SOURCES)) as pool:
        pending = [pool.submit(ensure_source, raw_dir, name, offline) for name in SOURCES]
        for completed in pending:
            completed.result()

    dates = calendar(FIRST_DATE, LAST_DATE)
    cases, missing_cases = load_time_series(raw_dir / "confirmed_global.csv", dates)
    deaths, missing_deaths = load_time_series(raw_dir / "deaths_global.csv", dates)
    if cases.keys() != deaths.keys() or len(cases) != 201:
        raise ValueError("Case and death time series must describe the same 201 reporting locations")
    cumulative_by_metric = {"cases": cases, "deaths": deaths}
    geography = load_geography(raw_dir / "locations.csv")
    if cases.keys() - geography.keys():
        raise ValueError(f"Missing geography for {sorted(cases.keys() - geography.keys())}")
    country_rows = [(country_id(name), name, *geography[name]) for name in sorted(cases)]
    if len({row[0] for row in country_rows}) != len(country_rows):
        raise ValueError("Reporting locations must have unique country IDs")
    snapshot = load_snapshot(raw_dir / "final_daily_report.csv")

    out_dir.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".pipeline-", dir=out_dir) as staging:
        destination = Path(staging)
        write_dimensions(destination, dates, country_rows)
        metrics, weekly_count = write_facts(destination, dates, country_rows, cumulative_by_metric)
        crosscheck(cumulative_by_metric, snapshot, metrics)
        metrics["cases"]["source_component_missing_cells"] = missing_cases
        metrics["deaths"]["source_component_missing_cells"] = missing_deaths
        quality = {
            "source": {
                "repository": REPO,
                "revision": REVISION,
                "license": "CC BY 4.0",
                "sources": {
                    name: {"url": f"{RAW_URL}/{suffix}", "sha256": digest}
                    for name, (suffix, digest) in SOURCES.items()
                },
            },
            "coverage": {
                "first_date": dates[0].isoformat(),
                "last_date": dates[-1].isoformat(),
                "dates": len(dates),
                "reporting_locations": len(country_rows),
                "country_days": len(dates) * len(country_rows),
                "weekly_rows": weekly_count,
                "iso3_missing": [row[1] for row in country_rows if not row[2]],
                "map_coordinates_missing": [row[1] for row in country_rows if not row[3] or not row[4]],
            },
            "metrics": metrics,
            "policies": POLICIES,
        }
        (destination / "quality.json").write_text(json.dumps(quality, indent=2) + "\n", encoding="utf-8")
        (destination / "quality.md").write_text(quality_markdown(quality), encoding="utf-8")
        for result in sorted(destination.iterdir()):
            result.replace(out_dir / result.name)
    return quality


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, default=Path("data/raw"), help="cache for pinned source CSVs")
    parser.add_argument("--out", type=Path, default=Path("data/processed"), help="analytics output directory")
    parser.add_argument("--offline", action="store_true", help="require checksum-valid cached inputs")
    args = parser.parse_args()
    try:
        quality = build(args.raw, args.out, args.offline)
    except (OSError, csv.Error, ValueError) as error:
        parser.exit(1, f"Pipeline failed: {error}\n")
    coverage = quality["coverage"]
    print(f"Wrote {coverage['country_days']:,} country-days and {coverage['weekly_rows']:,} location-weeks to {args.out}")


if __name__ == "__main__":
    main()
