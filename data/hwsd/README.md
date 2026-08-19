# HWSD v2.0 dataset — Somalia clip (for Laboratory auto-fill)

The engine samples this offline raster whenever a field has **no manual lab
reading**. A manual entry always overrides these values.

## What to place here
| file | produced from | how |
|---|---|---|
| `hwsd2_somalia.tif` | `HWSD2_RASTER` (global, band 1 = SMU id) | In **QGIS**: load the global raster → *Raster ▸ Extraction ▸ Clip Raster by Extent* → draw the Somalia extent (lon 40.97–51.42, lat −1.66–12.02) → save as **UInt16 GTiff** (keep nodata = 0) into this folder as `hwsd2_somalia.tif`. Clipping keeps the engine fast — the global file is ~2 GB, the Somali clip is only a few MB. |
| `hwsd2_layers.csv` | `HWSD2_DB.mdb` (Access) | Open the `.mdb` in **Access** (or LibreOffice Base / `mdbtools`: `mdb-export HWSD2_DB.mdb HWSD2_LAYERS > hwsd2_layers.csv`) and export the layer-attribute table to CSV. Columns the engine reads (first match wins): `HWSD2_SMU_ID`, `SEQUENCE` (1 = 0–20 cm topsoil), `PH`, `N`, `OC`, `CEC`, `CLAY`, `SAND`, `SILT`, `WRB4`. |

If the WSMU attribute export instead gives you `MU_GLOBAL`, that key is accepted too.

## Wire-up (already done in `docker-compose.yml`)
```
AGRI_HWSD_RASTER=/data/hwsd/hwsd2_somalia.tif
AGRI_HWSD_ATTRS=/data/hwsd/hwsd2_layers.csv
```
After dropping the two files in: `docker compose up -d --build`. The `/dashboard`
Laboratory sidebar button **"Auto-fill from HWSD"** (and the automatic probe on
every new polygon) then returns pH / organic-matter / texture for the field
location with `source: FAO/IIASA HWSD v2.0`.

Missing or partial files are safe: the API answers `available:false` and the
dashboard simply keeps the built-in 18-region baseline.
