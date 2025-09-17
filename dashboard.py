import json
import pandas as pd
import numpy as np
import geopandas as gpd
import plotly.express as px
from dash import html, dcc, Input, Output, ctx, no_update
import dash


# ─── LOAD DATA ────────────────────────────────────────────────────────────────
# Load preprocessed dashboard dataset
df = pd.read_csv("data/merged_df_dashboard.csv", low_memory=False)
df.loc[:, df.columns.str.startswith('manufacturing_emissions_')] /= 10

# Load municipalities shapefile (for map boundaries)
municipals = gpd.read_file(
    'data/ssb_municipalities_masks/Kommuner 2024.shp'
)
municipals["kommunenum"] = municipals["kommunenum"].astype(str).str.zfill(4)
df["kommunenum"] = df["kommunenum"].astype(str).str.zfill(4)

# Reproject to WGS84 (lat/lon for Mapbox)
municipals = municipals.to_crs(epsg=4326)

# Simplify geometries slightly (reduces map rendering time)
municipals["geometry"] = municipals["geometry"].simplify(tolerance=0.001, preserve_topology=True)

# Convert to GeoJSON for Plotly
muni_geojson = json.loads(municipals.to_json())

# 🔹 Precompute municipality-level aggregations for speed
#    Instead of recalculating aggregations every callback, 
#    we group by municipality/material once at startup.
precomputed_maps = {}
for metric in ["material_stock", "material_emissions", "manufacturing_emissions"]:
    for scenario in ["mean", "max", "min"]:
        value_col = f"{metric}_{scenario}"
        precomputed_maps[(metric, scenario)] = (
            df.groupby(["kommunenum", "material"], as_index=False)[value_col].sum()
            .merge(municipals[["kommunenum", "kommunenav"]], on="kommunenum", how="left")
        )


# ─── APP LAYOUT ───────────────────────────────────────────────────────────────
app = dash.Dash(__name__)

app.layout = html.Div([
    html.H2("Norway Material Stock & Emissions Dashboard"),

    # Dropdowns to choose scenario and metric
    dcc.Dropdown(
        id="scenario-dropdown",
        options=[
            {"label": "Real-Life Scenario", "value": "mean"},
            {"label": "Worst-Case Scenario", "value": "max"},
            {"label": "Best-Case Scenario", "value": "min"},
        ],
        value="mean",
        clearable=False,
        style={"width": "300px", "marginRight": "20px", "display": "inline-block"}
    ),

    dcc.Dropdown(
        id="metric-dropdown",
        options=[
            {"label": "Material Stock", "value": "material_stock"},
            {"label": "Material Production Emissions", "value": "material_emissions"},
            {"label": "Manufacturing Emissions", "value": "manufacturing_emissions"},
        ],
        value="material_stock",
        clearable=False,
        style={"width": "300px", "display": "inline-block"}
    ),

    # Reset buttons
    html.Div([
        html.Button("Reset to All Norway", id="reset-button", n_clicks=0),
        html.Button("Reset to All Materials", id="reset-material-button", n_clicks=0,
                    style={"marginLeft": "10px"})
    ], style={"marginBottom": "10px"}),

    # Hidden stores to persist user selections across callbacks
    dcc.Store(id="selected-muni-store"),
    dcc.Store(id="selected-material-store"),

    # Layout: map on the left, charts & summary on the right
    html.Div([
        html.Div(
            dcc.Graph(id="norway-map", style={"height": "90vh"}),
            style={"flex": "0.9", "padding": "5px"}
        ),
        html.Div([
            html.Div(id="summary-text",
                     style={"textAlign": "center", "padding": "8px", "fontSize": "16px"}),
            dcc.Graph(id="chart-material-type", style={"height": "42vh", "marginBottom": "2vh"}),
            dcc.Graph(id="chart-type-cohort", style={"height": "44vh"})
        ], style={"flex": "1.1", "padding": "5px"})
    ], style={"display": "flex", "flexDirection": "row", "height": "90vh", "overflow": "hidden"})
])


# ─── STORE UPDATE CALLBACK ─────────────────────────────────────────────────────
# Keeps track of selected municipality & material across clicks and resets
@app.callback(
    Output("selected-muni-store", "data"),
    Output("selected-material-store", "data"),
    Input("norway-map", "clickData"),
    Input("chart-material-type", "clickData"),
    Input("reset-button", "n_clicks"),
    Input("reset-material-button", "n_clicks"),
    Input("selected-muni-store", "data"),
    Input("selected-material-store", "data"),
    prevent_initial_call=True
)
def update_selections(map_click, bar_click, reset_all, reset_mat, current_muni, current_material):
    triggered = [t["prop_id"].split(".")[0] for t in ctx.triggered]

    muni_sel = current_muni
    mat_sel = current_material

    # Update municipality when user clicks on map
    if "norway-map" in triggered and map_click:
        muni_sel = map_click["points"][0]["location"]

    # Update material when user clicks on bar chart
    if "chart-material-type" in triggered and bar_click:
        mat_sel = bar_click["points"][0]["y"]

    # Reset buttons
    if "reset-button" in triggered:
        muni_sel = None
    if "reset-material-button" in triggered:
        mat_sel = None

    return muni_sel, mat_sel


# ─── MAIN DASHBOARD CALLBACK ───────────────────────────────────────────────────
# Updates map, both bar charts, and summary text based on user selections
@app.callback(
    Output("norway-map", "figure"),
    Output("chart-material-type", "figure"),
    Output("chart-type-cohort", "figure"),
    Output("summary-text", "children"),
    Input("scenario-dropdown", "value"),
    Input("metric-dropdown", "value"),
    Input("selected-muni-store", "data"),
    Input("selected-material-store", "data")
)
def update_dashboard(scenario, metric, selected_muni, selected_material):
    divisor = 1_000_000  # scale to kilotons

    # Configure chart settings depending on metric
    if metric == "material_stock":
        prefix = "material_stock"
        map_title = "Material Stock by Municipality"
        bar1_title = "Stock by Material Type"
        bar2_title = "Stock by Building Type & Cohort"
        unit_label = "kt"
        df_filtered = df.loc[df["energy_carrier"] == "TOTAL"]
        chart_mode = "material"
    elif metric == "material_emissions":
        prefix = "material_emissions"
        map_title = "Material Production Emissions by Municipality"
        bar1_title = "Production Emissions by Material Type"
        bar2_title = "Production Emissions by Building Type & Cohort"
        unit_label = "kt CO₂e"
        df_filtered = df.loc[df["energy_carrier"] == "TOTAL"]
        chart_mode = "material"
    else:  # manufacturing emissions
        prefix = "manufacturing_emissions"
        map_title = "Manufacturing Emissions by Municipality"
        bar1_title = "Manufacturing Emissions by Type & Energy Carrier"
        bar2_title = "Manufacturing Emissions by Building Type & Cohort"
        unit_label = "kt CO₂e"
        df_filtered = df
        chart_mode = "energy_type"

    value_col = f"{prefix}_{scenario}"

    # 🔹 Load precomputed municipality totals
    df_map = precomputed_maps[(metric, scenario)]

    # Apply material filter if selected
    if selected_material and selected_material != "TOTAL":
        df_filtered = df_filtered.loc[df_filtered["material"] == selected_material]
        df_map = df_map.loc[df_map["material"] == selected_material]

    # Default to TOTAL materials
    if not selected_material:
        df_map = df_map.loc[df_map["material"] == "TOTAL"]

    # Scale map values
    df_map[value_col] = (df_map[value_col] / divisor).round(1)
    # Avoid log of zero or negative values
    df_map["log_" + value_col] = np.log10(df_map[value_col].clip(lower=1e-6))  

    # Build map figure
    fig_map = px.choropleth_mapbox(
        df_map, geojson=muni_geojson, locations="kommunenum",
        featureidkey="properties.kommunenum", color="log_" + value_col,  # use log-transformed column,
        color_continuous_scale="viridis", mapbox_style="carto-positron",
        zoom=3.5, center={"lat": 64, "lon": 15}, opacity=0.6,
        title=map_title, labels={value_col: unit_label},
        hover_data={"kommunenum": True, "kommunenav": True, value_col: True}
    )

    # Highlight selected municipality with a red outline
    if selected_muni:
        sel = municipals.loc[municipals["kommunenum"] == selected_muni]
        fig_map.add_trace(
            px.choropleth_mapbox(
                sel, geojson=json.loads(sel.to_json()),
                locations="kommunenum", featureidkey="properties.kommunenum",
                color_discrete_sequence=["#FF0000"]
            ).data[0]
        )
        fig_map.data[-1].marker.opacity = 0.4
        fig_map.data[-1].marker.line.width = 3

    fig_map.update_layout(
        title={"text": map_title, "x": 0.01, "xanchor": "left", "font": {"size": 16}},
        margin={"r": 0, "t": 30, "l": 0, "b": 0},
        coloraxis_colorbar=dict(
            title=unit_label,
            tickvals=np.log10([1, 10, 100, 1000, 10000, 100000]),  # adjust to your value range
            ticktext=["1", "10", "100", "1000", "10000", "100000"]   # original values for readability
        )
    )

    # 🔹 Filter dataset for summary + bar charts
    if selected_muni:
        muni_name = municipals.set_index("kommunenum").at[selected_muni, "kommunenav"]
        sub = df_filtered.loc[df_filtered["kommunenum"] == selected_muni]
    else:
        muni_name = "all Norway"
        sub = df_filtered

    # Compute total value for summary text
    if chart_mode == "material":
        sub_total = sub.loc[sub["material"] == "TOTAL"]
    else:
        sub_total = sub.loc[sub["energy_carrier"] == "TOTAL"]

    total_val = (
        sub_total[value_col].sum() if not sub_total.empty else sub[value_col].sum()
    ) / divisor

    metric_label = {
        "material_stock": "material stock",
        "material_emissions": "material production emissions",
        "manufacturing_emissions": "manufacturing emissions"
    }[metric]

    if chart_mode == "material" and selected_material and selected_material != "TOTAL":
        title_left = f"{selected_material.title()} {metric_label}"
    else:
        title_left = metric_label.capitalize()

    # Summary text box
    summary = html.Div([
        html.Div(
            f"{title_left} in {muni_name}: {total_val:,.1f} {unit_label}",
            style={
                "color": "#DC143C", "fontSize": "25px", "fontWeight": "bold",
                "fontFamily": "Arial, sans-serif", "backgroundColor": "#e6ecf5",
                "padding": "10px", "borderRadius": "8px", "boxShadow": "0 2px 4px rgba(0,0,0,0.1)",
                "textAlign": "center"
            }
        )
    ])

    # 🔹 First bar chart: by material OR by energy carrier
    if chart_mode == "material":
        data1 = sub.loc[sub["material"] != "TOTAL"]
        df1 = data1.groupby("material", as_index=False)[value_col].sum().round(1)
        df1[value_col] = (df1[value_col] / divisor).round(1)

        # Add contextual stock & emissions values for hover info
        stock = data1.groupby("material")["material_stock_mean"].sum() / divisor
        emissions = data1.groupby("material")["material_emissions_mean"].sum() / divisor
        df1["stock"] = df1["material"].map(stock).round(1)
        df1["emissions"] = df1["material"].map(emissions).round(1)

        hover = {}
        if metric == "material_stock":
            hover = {"emissions": True}
        if metric == "material_emissions":
            hover = {"stock": True}

        fig_bar1 = px.bar(
            df1, x=value_col, y="material", orientation="h",
            color="material", color_discrete_sequence=px.colors.qualitative.Set2,
            title=f"{bar1_title} ({muni_name})",
            labels={"material": "Material Type", value_col: unit_label,
                    "stock": "Stock [kt]", "emissions": "Emissions [kt CO₂e]"},
            hover_data=hover
        )
        fig_bar1.update_layout(
            showlegend=False, yaxis={"categoryorder": "total ascending"},
            title={"text": f"{bar1_title} ({muni_name})", "x": 0.5, "font": {"size": 18}}
        )
    else:
        data1 = sub.loc[sub["energy_carrier"] != "TOTAL"]
        df1 = data1.groupby(["type", "energy_carrier"], as_index=False)[value_col].sum()
        df1[value_col] = (df1[value_col] / divisor).round(1)
        fig_bar1 = px.bar(
            df1, x=value_col, y="type", orientation="h",
            color="energy_carrier", barmode="stack",
            color_discrete_sequence=px.colors.qualitative.Set2,
            title=f"{bar1_title} ({muni_name})",
            labels={"type": "Building Type", "energy_carrier": "Energy Carrier", value_col: unit_label}
        )
        fig_bar1.update_layout(
            yaxis={"categoryorder": "total ascending"},
            legend_title_text="Energy Carrier"
        )

    # 🔹 Second bar chart: by building type & cohort
    if chart_mode == "material":
        data2 = sub.loc[sub["material"] != "TOTAL"]
    else:
        data2 = sub.loc[sub["energy_carrier"] != "TOTAL"]

    df2 = data2.groupby(["type", "cohort"], as_index=False)[value_col].sum()
    df2[value_col] = (df2[value_col] / divisor).round(1)

    fig_bar2 = px.bar(
        df2, x=value_col, y="type", orientation="h",
        color="cohort", barmode="stack",
        color_discrete_sequence=px.colors.qualitative.Set3,
        title=f"{bar2_title} ({muni_name})",
        labels={"type": "Building Type", "cohort": "Cohort", value_col: unit_label}
    )
    fig_bar2.update_layout(
        yaxis={"categoryorder": "total ascending"},
        title={"text": f"{bar2_title} ({muni_name})", "x": 0.5, "font": {"size": 18}},
        legend_title_text="Cohort",
        legend=dict(orientation="v", y=1, x=1.02, xanchor="left", yanchor="top")
    )

    return fig_map, fig_bar1, fig_bar2, summary


# ─── LAUNCH ───────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True)
