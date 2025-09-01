# Norway Material Stock & Emissions Dashboard

This repository hosts a Dash application for interactive exploration of material stocks and embodied CO₂ emissions across Norwegian municipalities.

It is possible to:
- Switch between real-life, worst-case and best-case scenarios
- Select different metrics (Material Stock, Material Production Emissions, Manufacturing Emissions)
- Drill down by municipality or material type

---

## Objective

The objective of the dashboard is to provide an interactive and user-friendly tool that enables local stakeholders, researchers and policymakers to explore and analyze material stocks and associated CO₂ emissions across Norwegian municipalities. By offering scenario comparisons, customizable metrics, and detailed breakdowns by municipality and material type, the dashboard supports informed decision-making aimed at sustainable resource management and climate impact reduction.

---

## Prerequisites

- Python 3.11.5 or higher
- Install required packages:

```bash
pip install pandas geopandas plotly dash jupyter-dash
```

---

## Data Requirements

### 1. Municipality shapefile
- Files: .shp, .dbf, .shx, etc.
- Coordinate system: EPSG:4326
- Required attributes:
  - kommunenum — municipality code (string, zero-padded to 4 digits)
  - kommunenav — municipality name
  - geometry — polygon geometry

### 2. Merged CSV with data
- File name: merged_df_dashboard.csv
- Structure: One row per combination of municipality, material, energy carrier, building type and cohort.
- Required columns:
  - kommunenum — string, zero-padded to 4 digits (this column represents municipality code)
  - energy_carrier — e.g. "TOTAL", "electricity", etc.
  - material — e.g. "TOTAL", "steel", "concrete", etc.
  - type — building type (e.g. single-family house (SFH), apartment block (AB))
  - cohort — year or cohort label
  - material_stock_mean — float (in kg before scaling)
  - material_stock_min — float
  - material_stock_max — float
  - material_emissions_mean — float (in kg CO₂e before scaling)
  - material_emissions_min — float
  - material_emissions_max — float
  - manufacturing_emissions_mean — float (in kg CO₂e before scaling)
  - manufacturing_emissions_min — float
  - manufacturing_emissions_max — float

---

## Project Folder Structure
```
/your-project-root
│
├── dashboard.py                  # Main Dash application script
├── merged_df_dashboard.csv       # Merged data CSV (municipality, materials, emissions)
├── /shapefiles                   # Folder containing municipality shapefile components
│   ├── municipalities.shp
│   ├── municipalities.dbf
│   ├── municipalities.shx
│   └── ...                      # Other shapefile support files                      
├── requirements.txt             # (Optional) List of required Python packages
└── README.md 
```
---

## Running the Dashboard

From the command line, navigate to the project root and execute:

```bash
python dashboard.py
```

If successful, you should see output like:

Dash app running on http://127.0.0.1:8050/
