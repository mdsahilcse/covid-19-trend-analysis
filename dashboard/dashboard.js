"use strict";

const byId = id => document.getElementById(id);
const dateFormat = new Intl.DateTimeFormat("en", {dateStyle: "medium", timeZone: "UTC"});
const monthFormat = new Intl.DateTimeFormat("en", {month: "short", year: "numeric", timeZone: "UTC"});
const dayFormat = new Intl.DateTimeFormat("en", {month: "short", day: "numeric", timeZone: "UTC"});
const whole = new Intl.NumberFormat("en-US");
const fraction = new Intl.NumberFormat("en-US", {maximumFractionDigits: 1});
const compact = new Intl.NumberFormat("en", {notation: "compact", maximumFractionDigits: 1});
const metricNames = {cases: "cases", deaths: "deaths"};
const colors = ["#2459ca", "#087c75"];
const mapColors = ["#e6eeff", "#c8d9fb", "#9ab7f1", "#658ad9", "#3464c4", "#183b8c"];
const svgNs = "http://www.w3.org/2000/svg";

let countries;
let byIso;
let calendar;
let firstDate;
let lastDate;
let shapes;
let dateline;
let metric = "cases";
let grain = "daily";
let plotState;
let activePoint = -1;

function node(tag, attrs = {}, content) {
  const element = document.createElementNS(svgNs, tag);
  for (const [key, value] of Object.entries(attrs)) {
    element.setAttribute(key, value);
  }
  if (content !== undefined) element.textContent = content;
  return element;
}

function parseCsv(text) {
  const rows = [];
  let row = [];
  let cell = "";
  let quoted = false;
  for (let index = 0; index < text.length; index++) {
    const char = text[index];
    if (char === '"') {
      if (quoted && text[index + 1] === '"') {
        cell += '"';
        index++;
      } else {
        quoted = !quoted;
      }
    } else if (!quoted && char === ",") {
      row.push(cell);
      cell = "";
    } else if (!quoted && (char === "\r" || char === "\n")) {
      if (char === "\r" && text[index + 1] === "\n") index++;
      row.push(cell);
      rows.push(row);
      row = [];
      cell = "";
    } else {
      cell += char;
    }
  }
  if (cell || row.length) rows.push([...row, cell]);
  const headers = rows.shift();
  if (!headers || quoted || rows.some(row => row.length !== headers.length)) {
    throw new Error("Invalid CSV archive format.");
  }
  return rows.map(row => Object.fromEntries(headers.map((name, index) => [name, row[index]])));
}

async function fetchFile(path, parse) {
  const response = await fetch(path);
  if (!response.ok) throw new Error(path + " returned HTTP " + response.status);
  return parse === "json" ? response.json() : parseCsv(await response.text());
}

function formatDate(date, formatter = dateFormat) {
  return formatter.format(new Date(date + "T00:00:00Z"));
}

const nullableNumber = value => value === "" || value === undefined ? null : Number(value);

function makeArchive(locationRows, dateRows, dailyRows) {
  const locations = new Map();
  for (const row of locationRows) {
    locations.set(row.country_id, {
      name: row.country_name,
      iso: row.iso3,
      id: row.country_id,
      days: new Map(),
    });
  }
  for (const row of dailyRows) {
    const country = locations.get(row.country_id);
    if (!country) throw new Error("Daily row has an unrecognized location.");
    country.days.set(row.report_date, {
      cases: nullableNumber(row.cases_daily),
      deaths: nullableNumber(row.deaths_daily),
      casesCumulative: nullableNumber(row.cases_cumulative),
      deathsCumulative: nullableNumber(row.deaths_cumulative),
      casesAverage: nullableNumber(row.cases_avg_7d),
      deathsAverage: nullableNumber(row.deaths_avg_7d),
    });
  }
  if (!dateRows.length || !locations.size || !dailyRows.length) {
    throw new Error("No data in the generated archive.");
  }
  return locations;
}

function selectCountry(id) {
  if (id === byId("compare-country").value) {
    byId("compare-country").value = byId("primary-country").value;
  }
  byId("primary-country").value = id;
  render();
}

function getSelection() {
  const selected = [byId("primary-country").value, byId("compare-country").value];
  return [...new Set(selected.filter(id => countries.has(id)))].map(id => countries.get(id));
}

function setControlsState() {
  for (const key of Object.keys(metricNames)) {
    byId("metric-" + key).setAttribute("aria-pressed", metric === key);
  }
  for (const key of ["daily", "weekly", "cumulative"]) {
    byId("grain-" + key).setAttribute("aria-pressed", grain === key);
  }
}

function total(values) {
  let value = 0;
  let count = 0;
  for (const item of values) {
    if (item === null || item === undefined) continue;
    value += item;
    count++;
  }
  return count ? value : null;
}

function selectedNet(locations, dates, key) {
  return total(locations.flatMap(location => dates.map(date => location.days.get(date)?.[key])));
}

function renderKpis(locations, dates) {
  const scope = locations.length === 1 ? locations[0].name : "Both selected locations";
  for (const key of ["cases", "deaths"]) {
    const count = selectedNet(locations, dates, key);
    byId("total-" + key).textContent = count === null ? "—" : whole.format(count);
    byId(key + "-caption").textContent = scope + " · net change in selected dates";
  }
  let peakDate;
  let peak = -Infinity;
  for (const date of dates) {
    const values = locations.map(place => place.days.get(date)?.[metric]);
    if (values.some(value => value === null || value === undefined)) continue;
    const value = total(values);
    if (value > peak) {
      peakDate = date;
      peak = value;
    }
  }
  byId("peak-value").textContent = peakDate ? whole.format(peak) : "—";
  byId("peak-caption").textContent = peakDate ? metricNames[metric] + " · " + formatDate(peakDate) : "No observed value in selected dates";
}

function buildPoints(dates, locations) {
  if (grain === "weekly") {
    const buckets = new Map();
    for (const date of dates) {
      const week = calendar.get(date);
      if (!buckets.has(week)) buckets.set(week, []);
      buckets.get(week).push(date);
    }
    return [...buckets.entries()].map(([week, days]) => ({
      date: week,
      days,
      values: locations.map(place => total(days.map(day => place.days.get(day)?.[metric]))),
    }));
  }
  const valueKey = grain === "cumulative" ? metric + "Cumulative" : metric;
  return dates.map(date => ({
    date,
    days: [date],
    values: locations.map(place => place.days.get(date)?.[valueKey] ?? null),
    averages: locations.map(place => place.days.get(date)?.[metric + "Average"] ?? null),
  }));
}

function axisBounds(points) {
  let low = 0;
  let high = 0;
  for (const point of points) {
    const values = grain === "daily" ? point.values.concat(point.averages) : point.values;
    for (const value of values) {
      if (value === null) continue;
      low = Math.min(low, value);
      high = Math.max(high, value);
    }
  }
  if (high === low) high = low + 4;
  const roughUnit = (high - low) / 4;
  const scale = 10 ** Math.floor(Math.log10(roughUnit));
  const unit = scale * [1, 2, 2.5, 5, 10].find(value => value >= roughUnit / scale);
  return [Math.floor(low / unit) * unit, Math.ceil(high / unit) * unit, unit];
}

function trendLine(points, valueKey, index, x, y) {
  const segments = [];
  let segment = null;
  for (const [position, point] of points.entries()) {
    const value = point[valueKey][index];
    if (value === null) {
      segment = null;
      continue;
    }
    const coordinate = [x(position), y(value)];
    if (!segment) {
      segment = [];
      segments.push(segment);
    }
    segment.push(coordinate);
  }
  const color = colors[index];
  const raw = grain === "daily" && valueKey === "values";
  const pathData = segments.filter(part => part.length > 1)
    .map(part => "M" + part.map(([x, y]) => x.toFixed(1) + "," + y.toFixed(1)).join("L")).join("");
  const elements = [];
  if (pathData) {
    elements.push(node("path", {
      d: pathData, stroke: color, "stroke-width": raw ? 1.3 : 2.3, class: raw ? "series raw-series" : "series",
    }));
  }
  for (const part of segments.filter(part => part.length === 1)) {
    elements.push(node("circle", {cx: part[0][0], cy: part[0][1], r: 2.2, fill: color}));
  }
  return elements;
}

function renderTrend(locations, dates) {
  const points = buildPoints(dates, locations);
  const format = grain === "weekly" ? "Weekly" : grain === "cumulative" ? "Cumulative" : "Daily";
  byId("trend-title").textContent = format + " reported " + metricNames[metric];
  byId("trend-caption").textContent = locations.map(place => place.name).join(" compared with ");
  byId("chart-note").textContent = {
    daily: "The stronger lines show trailing 7-day averages. Faint lines show daily reports.",
    weekly: "Weeks start on Monday. Select a point to drill into its daily reports. Partial weeks use only selected dates.",
    cumulative: "Accumulated reports since the archive began. Corrections can reduce the total.",
  }[grain];

  const legend = byId("chart-legend");
  legend.replaceChildren();
  locations.forEach((place, index) => {
    const item = document.createElement("span");
    const key = document.createElement("i");
    key.style.setProperty("--series", colors[index]);
    item.append(key, document.createTextNode(place.name));
    legend.append(item);
  });

  const chart = byId("trend-chart");
  chart.classList.toggle("is-weekly", grain === "weekly");
  const width = chart.clientWidth < 520 ? 480 : 1040;
  chart.setAttribute("viewBox", "0 0 " + width + " 262");
  chart.replaceChildren();
  const left = 48;
  const right = width - 23;
  const top = 10;
  const bottom = 231;
  const [minimum, maximum, unit] = axisBounds(points);
  const x = step => points.length === 1 ? (left + right) / 2 : left + step * (right - left) / (points.length - 1);
  const y = value => bottom - (value - minimum) * (bottom - top) / (maximum - minimum);

  for (let step = minimum; step <= maximum + unit / 100; step += unit) {
    const level = y(step);
    chart.append(node("line", {x1: left, x2: right, y1: level, y2: level, class: step === 0 ? "zero" : "grid"}));
    chart.append(node("text", {x: left - 8, y: level + 4, "text-anchor": "end"}, compact.format(step)));
  }
  const tickCount = Math.min(points.length, width < 520 ? 5 : 8);
  for (let tick = 0; tick < tickCount; tick++) {
    const position = tickCount === 1 ? 0 : Math.round(tick * (points.length - 1) / (tickCount - 1));
    const first = tick === 0 && tickCount > 1;
    const last = tick === tickCount - 1 && tickCount > 1;
    const format = dates.length <= 150 ? dayFormat : monthFormat;
    chart.append(node("text", {
      x: x(position), y: bottom + 18, "text-anchor": first ? "start" : last ? "end" : "middle",
    }, formatDate(points[position].date, format)));
  }

  for (const index of locations.keys()) {
    chart.append(...trendLine(points, "values", index, x, y));
  }
  if (grain === "daily") {
    for (const index of locations.keys()) {
      chart.append(...trendLine(points, "averages", index, x, y));
    }
  }

  const cursor = node("g", {visibility: "hidden"});
  chart.append(cursor);
  plotState = {points, locations, width, left, right, top, bottom, x, y, cursor};
  hideCursor();
}

function renderMap(end, primary) {
  const map = byId("case-map");
  const focusedCountry = document.activeElement.dataset?.location;
  map.replaceChildren();
  const key = metric + "Cumulative";
  const values = [...countries.values()]
    .map(place => ({place, value: place.days.get(end)?.[key]}))
    .filter(item => item.value !== null && item.value !== undefined)
    .sort((a, b) => b.value - a.value);
  const maximum = values[0]?.value ?? 0;
  const color = value => {
    if (value === null || value === undefined) return "#e4e9ef";
    const band = maximum === 0 ? 0 : Math.floor(Math.log1p(Math.max(0, value)) / Math.log1p(maximum) * mapColors.length);
    return mapColors[Math.min(mapColors.length - 1, band)];
  };

  byId("map-caption").textContent = "Cumulative reported " + metricNames[metric] + " through " + formatDate(end);
  const dots = [];
  for (const shape of shapes) {
    const place = byIso.get(shape.code);
    const count = place?.days.get(end)?.[key];
    const path = node("path", {d: shape.path, fill: color(count)});
    path.append(node("title", {}, place ? place.name + " · " + (count === null || count === undefined ? "No observation" : whole.format(count)) : shape.name));
    if (place) {
      path.setAttribute("role", "button");
      path.setAttribute("tabindex", "0");
      path.setAttribute("aria-label", place.name + ", " + (count === null || count === undefined ? "no observation" : whole.format(count) + " reported " + metricNames[metric]));
      path.setAttribute("aria-pressed", place.id === primary.id);
      path.dataset.location = place.id;
      path.addEventListener("click", () => selectCountry(place.id));
      path.addEventListener("keydown", event => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          selectCountry(place.id);
        }
      });
    }
    dots.push(path);
  }
  map.append(...dots);
  const focusedPath = dots.find(path => path.dataset.location && path.dataset.location === focusedCountry);
  focusedPath?.focus();
  renderRanking(values.slice(0, 6), end, maximum);
}

function renderRanking(values, end, maximum) {
  const ranking = byId("ranking");
  ranking.replaceChildren();
  byId("ranking-title").textContent = "Highest reported " + (metric === "cases" ? "case" : "death") + " totals";
  byId("ranking-caption").textContent = "All reporting locations · " + formatDate(end);
  for (const {place, value} of values) {
    const item = document.createElement("li");
    const button = document.createElement("button");
    button.type = "button";
    const name = document.createElement("span");
    name.textContent = place.name;
    const count = document.createElement("span");
    count.className = "rank-value";
    count.textContent = whole.format(value);
    const track = document.createElement("span");
    track.className = "rank-track";
    track.setAttribute("aria-hidden", "true");
    const bar = document.createElement("span");
    bar.className = "rank-width";
    bar.style.width = (maximum > 0 ? Math.max(0, value / maximum) * 100 : 0) + "%";
    track.append(bar);
    button.append(name, count, track);
    button.addEventListener("click", () => {
      selectCountry(place.id);
      byId("primary-country").focus({preventScroll: true});
    });
    item.append(button);
    ranking.append(item);
  }
}

function hideCursor() {
  activePoint = -1;
  byId("chart-tooltip").hidden = true;
  plotState?.cursor.setAttribute("visibility", "hidden");
}

function showCursor(index) {
  if (index === activePoint || !plotState) return;
  const {points, locations, x, y, top, bottom, cursor, width} = plotState;
  const point = points[index];
  if (!point) return;
  activePoint = index;
  const chartX = x(index);
  cursor.setAttribute("visibility", "visible");
  cursor.replaceChildren(node("line", {x1: chartX, x2: chartX, y1: top, y2: bottom, class: "cursor"}));
  const tooltip = byId("chart-tooltip");
  const title = document.createElement("strong");
  title.textContent = grain === "weekly" ? "Week of " + formatDate(point.date) : formatDate(point.date);
  tooltip.replaceChildren(title);
  locations.forEach((place, number) => {
    const value = point.values[number];
    const row = document.createElement("div");
    const average = grain === "daily" ? point.averages[number] : null;
    row.textContent = place.name + " · " + (value === null ? "Missing" : whole.format(value)) +
      (average === null ? "" : " · 7-day avg " + fraction.format(average));
    tooltip.append(row);
    if (value !== null) {
      cursor.append(node("circle", {cx: chartX, cy: y(value), r: 3.5, fill: colors[number], stroke: "#fff", "stroke-width": 1}));
    }
  });
  tooltip.hidden = false;
  const chartWidth = byId("trend-chart").getBoundingClientRect().width;
  const xPixel = chartX * chartWidth / width;
  tooltip.style.left = Math.max(0, Math.min(chartWidth - tooltip.offsetWidth, xPixel + 11)) + "px";
  tooltip.style.top = "13px";
  byId("trend-chart").setAttribute("aria-label", tooltip.textContent);
}

function pointAt(event) {
  const chart = byId("trend-chart");
  const box = chart.getBoundingClientRect();
  const {width, left, right, points} = plotState;
  if (!box.width) return -1;
  const x = (event.clientX - box.left) * width / box.width;
  return Math.min(points.length - 1, Math.max(0, Math.round((x - left) / (right - left) * (points.length - 1))));
}

function drillWeek(index) {
  if (grain !== "weekly" || index < 0) return;
  const days = plotState.points[index].days;
  byId("start-date").value = days[0];
  byId("end-date").value = days.at(-1);
  grain = "daily";
  render();
}

function render() {
  const start = byId("start-date").value;
  const end = byId("end-date").value;
  const error = byId("date-error");
  const valid = calendar.has(start) && calendar.has(end) && start <= end;
  error.hidden = valid;
  if (!valid) {
    error.textContent = "Choose a start and end within the archive. The end date must be on or after the start date.";
    return;
  }
  const locations = getSelection();
  const dates = dateline.slice(dateline.indexOf(start), dateline.indexOf(end) + 1);
  setControlsState();
  renderKpis(locations, dates);
  renderTrend(locations, dates);
  renderMap(end, locations[0]);
}

function addControls() {
  for (const key of ["primary-country", "compare-country", "start-date", "end-date"]) {
    byId(key).addEventListener("change", event => {
      if (key === "primary-country" && event.target.value === byId("compare-country").value) {
        byId("compare-country").value = "";
      }
      if (key === "compare-country" && event.target.value === byId("primary-country").value) {
        event.target.value = "";
      }
      render();
    });
  }
  for (const key of Object.keys(metricNames)) {
    byId("metric-" + key).addEventListener("click", () => {
      metric = key;
      render();
    });
  }
  for (const key of ["daily", "weekly", "cumulative"]) {
    byId("grain-" + key).addEventListener("click", () => {
      grain = key;
      render();
    });
  }
  byId("reset-range").addEventListener("click", () => {
    byId("start-date").value = firstDate;
    byId("end-date").value = lastDate;
    render();
  });
  const chart = byId("trend-chart");
  chart.addEventListener("pointermove", event => showCursor(pointAt(event)));
  chart.addEventListener("pointerleave", hideCursor);
  chart.addEventListener("click", event => drillWeek(pointAt(event)));
  chart.addEventListener("blur", hideCursor);
  chart.addEventListener("keydown", event => {
    if (event.key === "Enter") {
      drillWeek(activePoint);
      return;
    }
    if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
      event.preventDefault();
      const offset = event.key === "ArrowLeft" ? -1 : 1;
      showCursor(Math.min(plotState.points.length - 1, Math.max(0, activePoint + offset)));
    }
  });
  window.matchMedia("(max-width: 600px)").addEventListener("change", render);
}

function addOptions() {
  const primary = byId("primary-country");
  const compare = byId("compare-country");
  compare.add(new Option("No comparison", ""));
  const locations = [...countries.values()].sort((a, b) => a.name.localeCompare(b.name, "en"));
  for (const {name, id} of locations) {
    primary.add(new Option(name, id));
    compare.add(new Option(name, id));
  }
  primary.value = countries.has("us") ? "us" : locations[0].id;
  compare.value = countries.has("india") ? "india" : "";
  const start = byId("start-date");
  const end = byId("end-date");
  start.min = end.min = firstDate;
  start.max = end.max = lastDate;
  start.value = firstDate;
  end.value = lastDate;
}

async function init() {
  const [countryRows, dateRows, dailyRows, geography] = await Promise.all([
    fetchFile("../data/processed/countries.csv"),
    fetchFile("../data/processed/dates.csv"),
    fetchFile("../data/processed/daily.csv"),
    fetchFile("assets/world.json", "json"),
  ]);
  countries = makeArchive(countryRows, dateRows, dailyRows);
  byIso = new Map([...countries.values()].filter(place => place.iso).map(place => [place.iso, place]));
  dateline = dateRows.map(row => row.report_date).sort();
  calendar = new Map(dateRows.map(row => [row.report_date, row.week_start]));
  firstDate = dateline[0];
  lastDate = dateline.at(-1);
  shapes = geography;
  byId("archive-range").textContent = formatDate(firstDate) + " – " + formatDate(lastDate);
  addOptions();
  addControls();
  byId("report").hidden = false;
  byId("status").hidden = true;
  render();
}

init().catch(error => {
  byId("status").textContent = "The archive could not load. Run the data pipeline, then open this page from an HTTP server started in the repository root.";
  console.error(error);
});
