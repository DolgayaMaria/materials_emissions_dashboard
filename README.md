# Norway Material Stock & Emissions Dashboard

This repository hosts a **Dash** application for interactive exploration of material stocks and CO₂ emissions across Norwegian municipalities.  

You can:
- Switch between *real-life*, *worst-case*, and *best-case* scenarios.
- Select different metrics.
- Drill down by municipality or material type.

---

## Prerequisites

- **Python** 3.8 or higher  
- Install required packages:  
```bash
pip install pandas geopandas numpy rasterio netCDF4 matplotlib seaborn plotly dash jupyter-dash

## Data Requirements

1. Municipality Shapefile
Files: .shp, .dbf, .shx, etc.
Coordinate system: EPSG:4326
Required attributes:
kommunenum — string, zero-padded to 4 digits (e.g. "0101")
kommunenav — municipality name
geometry — polygon geometry

2. Merged CSV
File name: merged_df_dashboard.csv
Structure: One row per combination of municipality, material, energy carrier, building type and cohort.

Required columns:
- kommunenum — string, zero-padded to 4 digits
- energy_carrier — e.g. "TOTAL", "electricity", etc.
- material — e.g. "TOTAL", "steel", "concrete", etc.
- type — building type (e.g. "single-family house (SFH)", "apartment block (AB)")
- cohort — year or cohort label
- material_stock_mean — float
- material_stock_min — float
- material_stock_max — float
- material_emissions_mean — float (in kg CO₂e before scaling)
- material_emissions_min — float
- material_emissions_max — float
- manufacturing_emissions_mean — float (in kg CO₂e before scaling)
- manufacturing_emissions_min — float
- manufacturing_emissions_max — float
