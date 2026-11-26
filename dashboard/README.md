# Browser dashboard

From the repository root, generate the processed data and start a static server.

```sh
python3 -m src.pipeline --out data/processed
python3 -m http.server 8000
```

Open [http://localhost:8000/dashboard/](http://localhost:8000/dashboard/). The browser reads the local pipeline outputs. It needs no JavaScript package installation or map service.

- Use the country selectors to compare up to two reporting locations.
- Choose cases or deaths, then daily, weekly, or cumulative reporting. The daily view overlays the trailing seven-day average on signed daily counts.
- Hover over the chart for exact values, or focus the chart and press the left or right arrow. In weekly view, select a chart point or press Enter to drill into that week. **Full period** restores the archive's date range.
- The map and ranking show end-date cumulative counts across the archive. Select a country on the map or in the ranking to update the trend. Use the country menu for smaller territories and other source reporting groups that have no map shape.

Map outlines and ISO identifiers come from the public-domain [Natural Earth 1:110m Admin 0 Countries, v5.1.2](https://github.com/nvkelso/natural-earth-vector/blob/v5.1.2/geojson/ne_110m_admin_0_countries.geojson). The dashboard simplifies the source to projected paths and joins ISO3 codes to the Johns Hopkins reporting locations. The boundaries and the geographic scope of the reporting series can differ. [Natural Earth terms of use](https://www.naturalearthdata.com/about/terms-of-use/)
