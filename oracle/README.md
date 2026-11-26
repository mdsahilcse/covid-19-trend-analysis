# Oracle analytics

Build the data exports, then run the SQL against Oracle Database Free using Docker.

```sh
python3 -m src.pipeline --out data/processed
bash oracle/run.sh
```

The runner uses a pinned multi-architecture Oracle Database Free 23.26.3 container, waits until its database is healthy, and mounts the SQL and CSVs as read-only inputs. It starts with a fresh database, publishes no ports, and removes its container when the run finishes. Allow time and disk space for the initial image download. To verify another export from the same pipeline, pass the directory as the first argument.

The runner prints the Oracle version, the reporting location and day counts, the number of matched daily and weekly rows, and confirmation that the refresh committed. Any validation or SQL error returns a nonzero status.

| Script | Purpose |
| --- | --- |
| `00_setup.sql` | Create the schema and file directory in `FREEPDB1`, then run the DDL. |
| `01_schema.sql` | Create the date and location dimensions, cumulative snapshot fact, and CSV staging tables. |
| `02_views.sql` | Compute signed daily changes, trailing seven-day means, cumulative totals, and Monday-based weekly metrics. |
| `03_refresh.sql` | Full refresh in one transaction, with verification before commit. Run it again in the same configured database to refresh the data. |
| `04_verify.sql` | Assert a complete country-day grid and compare every derived daily and weekly row with the Python output. |
| `05_queries.sql` | Compare locations, inspect daily trends, and measure data quality. |

The fact stores published cumulative observations. `v_country_daily` uses `LAG` for adjacent-day signed deltas and analytic `SUM` for cumulative reconstruction. After a gap, the next observed cumulative value starts a new baseline and that day's change is unknown. Seven-day averages require seven known daily changes. The weekly view reports the sum of known changes and the coverage for each measure.

The container setup uses the default `FREEPDB1` pluggable database and reads CSVs from `/input`. For a separate Oracle instance, configure an equivalent server-side directory and a schema with permissions to create the tables and views, then run the DDL and refresh with the appropriate connection. The sample queries use the [star schema](../docs/schema.md).
