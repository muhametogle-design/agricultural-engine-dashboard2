# HWSD v2.0 dataset — Somalia clip (PRE-BUILT, ready to use)

The files in this folder were produced directly from the official FAO/IIASA
downloads (`HWSD2_RASTER.zip` + `HWSD2_DB.zip`):

| file | what it is |
|---|---|
| `hwsd2_somalia.tif` | Somalia-extent clip (lon 40.9–51.5, lat −1.8–12.2) of the global HWSD v2.0 Soil-Mapping-Unit grid, 30 arc-second (~1 km), nodata re-coded to 0, Deflate GTiff (**≈220 KB** instead of 1.9 GB). |
| `hwsd2_layers.csv` | All 4,018 attribute rows for the 297 SMUs appearing in the clip: `PH_WATER, ORG_CARBON, TOTAL_N, CEC_SOIL, CLAY, SAND, SILT, WRB4, SHARE, SEQUENCE, TOPDEP`. |

Nothing else is needed — `docker-compose.yml` already mounts `./data` and sets:

```
AGRI_HWSD_RASTER=/data/hwsd/hwsd2_somalia.tif
AGRI_HWSD_ATTRS=/data/hwsd/hwsd2_layers.csv
```

`docker compose up -d --build` and the dashboard Laboratory panel auto-fills
pH / OM / N / texture from any drawn polygon (manual field values always win).
Land-cover placeholder pixels (SMU 7001 Technosols) are healed by sampling the
nearest profiled pixel within ~4 km; the response carries `nearest_km` when so.

## Rebuilding from scratch (optional)
1. Download `HWSD2_RASTER.zip` and `HWSD2_DB.zip` from the FAO Soils Portal.
2. rasterio: windowed read of `HWSD2.bil` over the Somalia bounds → write
   UInt16 GTiff with nodata 0.
3. `mdb-export HWSD2.mdb HWSD2_LAYERS` → keep rows whose `HWSD2_SMU_ID` occurs
   in the clip → drop unneeded columns → save CSV.

Missing or partial files are safe: the API answers `available:false` and the
dashboard silently keeps the built-in 18-region baseline.
