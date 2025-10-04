import pandas as pd
from dash import Dash, dcc, html, Input, Output, dash_table
import plotly.express as px
import geopandas as gpd

# ----------------------------
# Cargar datos
# ----------------------------
df = pd.read_csv("Precios_de_Combustibles_MinEnergia.csv")
df.columns = df.columns.str.lower()
df["codigodepartamento"] = df["codigodepartamento"].astype(int)

# ----------------------------
# Cargar shapefile y preparar
# ----------------------------
gdf = gpd.read_file("COLOMBIA/COLOMBIA.shp")
gdf["DPTO_CCDGO"] = gdf["DPTO_CCDGO"].astype(int)

# Preparamos estructura de lookup para choropleth (croquis completo)
gdf_base = gdf.copy()

# ----------------------------
# Precomputar datasets por filtro
# ----------------------------
data_cache = {}
for anio in df["periodo"].unique():
    for mes in df["mes"].unique():
        for producto in df["producto"].unique():
            key = (anio, mes, producto)
            dff = df[(df["periodo"] == anio) &
                     (df["mes"] == mes) &
                     (df["producto"] == producto)]
            data_cache[key] = dff

# ----------------------------
# Inicializar app
# ----------------------------
app = Dash(__name__)
server = app.server  # 👈 para Render

anios = sorted(df['periodo'].unique())
meses = sorted(df['mes'].unique())
productos = sorted(df['producto'].unique())

# ----------------------------
# Layout
# ----------------------------
app.layout = html.Div([
    html.H1("Dashboard de Precios de Combustibles en Colombia", 
            style={'textAlign': 'center'}),

    html.Div([
        html.Div([
            html.Label("Selecciona Año:"),
            dcc.Dropdown(
                id="filtro-anio",
                options=[{"label": i, "value": i} for i in anios],
                value=anios[0], clearable=False
            ),
        ], style={'width': '20%', 'display': 'inline-block', 'padding': '10px'}),

        html.Div([
            html.Label("Selecciona Mes:"),
            dcc.Dropdown(
                id="filtro-mes",
                options=[{"label": i, "value": i} for i in meses],
                value=meses[0], clearable=False
            ),
        ], style={'width': '20%', 'display': 'inline-block', 'padding': '10px'}),

        html.Div([
            html.Label("Selecciona Producto:"),
            dcc.Dropdown(
                id="filtro-producto",
                options=[{"label": i, "value": i} for i in productos],
                value=productos[0], clearable=False
            ),
        ], style={'width': '40%', 'display': 'inline-block', 'padding': '10px'}),
    ]),

    dcc.Graph(id="mapa-precios"),

    html.Div([
        dcc.Graph(id="barras-precios", style={'width': '48%', 'display': 'inline-block'}),
        dcc.Graph(id="boxplot-precios", style={'width': '48%', 'display': 'inline-block'}),
    ]),

    html.Div([
        html.Div([
            html.H3("Datos filtrados"),
            dash_table.DataTable(
                id="tabla-datos",
                columns=[{"name": i, "id": i} for i in ["periodo","mes","producto","nombredepartamento","municipio","precio"]],
                page_size=10,
                style_table={'overflowX': 'auto'},
                style_cell={'textAlign': 'left'},
                filter_action="native",
                sort_action="native"
            )
        ], style={'width': '48%', 'display': 'inline-block', 'verticalAlign': 'top'}),

        html.Div([dcc.Graph(id="mapa-coropletico")],
                 style={'width': '48%', 'display': 'inline-block'}),
    ])
])

# ----------------------------
# Callbacks optimizados
# ----------------------------
@app.callback(
    [Output("mapa-precios", "figure"),
     Output("barras-precios", "figure"),
     Output("boxplot-precios", "figure"),
     Output("tabla-datos", "data"),
     Output("mapa-coropletico", "figure")],
    [Input("filtro-anio", "value"),
     Input("filtro-mes", "value"),
     Input("filtro-producto", "value")]
)
def actualizar_dashboard(anio, mes, producto):
    dff = data_cache[(anio, mes, producto)]

    # Scatter simplificado (promedio por municipio)
    df_mun = dff.groupby("municipio")["precio"].mean().reset_index()
    fig_mapa = px.scatter(
        df_mun, x="municipio", y="precio",
        size="precio", color="precio",
        title=f"Precios promedio de {producto} en {mes} {anio}"
    )

    # Barras
    fig_barras = px.bar(
        dff.groupby("nombredepartamento")["precio"].mean().reset_index(),
        x="nombredepartamento", y="precio",
        title="Precio promedio por departamento"
    )

    # Boxplot
    fig_box = px.box(
        dff, x="nombredepartamento", y="precio",
        title="Distribución de precios"
    )

    # Choropleth
    dpto_mean = dff.groupby("codigodepartamento")["precio"].mean().reset_index()
    gdf_merged = gdf_base.merge(dpto_mean, left_on="DPTO_CCDGO",
                                right_on="codigodepartamento", how="left")

    fig_choro = px.choropleth(
        gdf_merged,
        geojson=gdf_merged.__geo_interface__,
        locations=gdf_merged.index,
        color="precio",
        projection="mercator",
        title=f"Mapa coroplético ({producto}, {mes} {anio})",
        labels={"precio": "Precio ($)"},
        color_continuous_scale="OrRd"
    )
    fig_choro.update_geos(fitbounds="locations", visible=False)
    fig_choro.update_traces(marker_line=dict(width=0.3, color="black"))

    return fig_mapa, fig_barras, fig_box, dff.to_dict("records"), fig_choro


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8050, debug=True)
# ----------------------------