import sys
import argparse
import dash
from dash import dcc, html, Input, Output, State
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import plotly.express as px
import os
from datetime import datetime, date
from functools import lru_cache
import re

NOISE_BANDS = [
    (40, "<40"),
    (45, "<45"),
    (50, "<50"),
    (55, "<55"),
    (60, "<60"),
    (65, "<65"),
    (70, "<69"),
    (75, "<74"),
    (80, "<80")
]

COLOR_VALUES = [
    "#238443",
    "#78C679",
    "#C2E699",
    "#FFFFB2",
    "#FECC5C",
    "#FD8D3C",
    "#FF0909",
    "#B30622",
    "#67033B",
    "#1C0054"
]

# Add the final "80+" band
LABELS = [label for _, label in NOISE_BANDS] + ["80+"]

color_map = dict(zip(LABELS, COLOR_VALUES))

def classify_noise_band(db):
    for threshold, _ in NOISE_BANDS:
        if db < threshold:
            return threshold
    return "80+"

# color_map = {
#     "0-39": "#238443",  # Moderate sea green
#     "40-44": "#78C679",  # Greyish green
#     "45-49": "#C2E699",  # Light greyish chartreuse green
#     "50-54": "#FFFFB2",  # Pale yellow
#     "55-59": "#FECC5C",  # Light brilliant amber
#     "60-64": "#FD8D3C",  # Brilliant tangelo
#     "65-69": "#FF0909",  # Light brilliant red
#     "70-74": "#B30622",  # Moderate amaranth
#     "75-79": "#67033B",  # Dark rose
#     "80+":   "#1C0054",  # Deep blue violet
# }

# def classify_noise_band(db):
#     if db < 35:
#         return "less than 35"
#     elif 35 <= db < 40:
#         return "35-39"
#     elif 40 <= db < 45:
#         return "40-44"
#     elif 45 <= db < 50:
#         return "45-49"
#     elif 50 <= db < 55:
#         return "50-54"
#     elif 55 <= db < 60:
#         return "55-59"
#     elif 60 <= db < 65:
#         return "60-64"
#     elif 65 <= db < 70:
#         return "65-69"
#     elif 70 <= db < 75:
#         return "70-74"
#     elif 75 <= db < 80:
#         return "75-79"
#     else:
#         return "80+"

def parse_args():
    parser = argparse.ArgumentParser(description="Plot dB receiver data as animated map.")
    parser.add_argument("directory", help="Directory containing CSV files")
    parser.add_argument("--zoom", type=int, default=15, help="Initial map zoom level (default: 13)")
    return parser.parse_args()

# 📁 Directory with your CSVs
# DATA_DIR = 'data/pisa/2024-11-07/test_map'
# PREFIX = 'pisa'
DATA_DIR = 'data/brindisi/2025-09-01/center/output'
PREFIX = 'brindisi'
TS_FORMAT = "%Y%m%d-%H%M-%A"

def extract_timestamp(filename):
    match = re.search(r"\d{8}-\d{4}-[A-Za-z]+", filename)
    if match:
        try:
            dt = datetime.strptime(match.group(), TS_FORMAT)
            return dt
        except:
            pass
    return filename

# ⏳ Discover all available timestamps from filenames
def get_all_timestamps():
    timestamps = []
    for fname in os.listdir(DATA_DIR):
        if fname.endswith('.csv'):
            try:
                ts = extract_timestamp(fname)
                timestamps.append(ts)

            except ValueError:
                continue
    return sorted(timestamps)

ALL_TIMESTAMPS = get_all_timestamps()
if not ALL_TIMESTAMPS:
    raise ValueError("No CSV files found in the 'data/' directory.")

ts_min = min(ALL_TIMESTAMPS)
ts_max = max(ALL_TIMESTAMPS)

min_date_str = ts_min.strftime('%Y-%m-%d')
max_date_str = ts_max.strftime('%Y-%m-%d')


# PISA
# def make_geodataframe(df):
#     geometry = [Point(xy) for xy in zip(df['X/m'], df['Y/m'])]
#     gdf = gpd.GeoDataFrame(df, geometry=geometry)
#     gdf.set_crs(epsg=3003, inplace=True)
#     gdf = gdf.to_crs(epsg=4326)
#     gdf["lon"] = gdf.geometry.x
#     gdf["lat"] = gdf.geometry.y
#     return gdf

# BRINDISI  EPSG:32633 WGS:8433N (UTM 33N)
def make_geodataframe(df):
    geometry = [Point(xy) for xy in zip(df['X/m'], df['Y/m'])]
    gdf = gpd.GeoDataFrame(df, geometry=geometry)
    gdf.set_crs(epsg=32633, inplace=True)
    gdf = gdf.to_crs(epsg=4326)
    gdf["lon"] = gdf.geometry.x
    gdf["lat"] = gdf.geometry.y
    return gdf

# 🧠 Cache file reads
@lru_cache(maxsize=64)
def load_data_for_timestamp(ts: datetime):
    # filename = ts.strftime('%Y-%m-%d_%H-%M') + '.csv'
    timestamp = ts.strftime(TS_FORMAT)
    filename = f'{PREFIX}-{timestamp}.csv'
    path = os.path.join(DATA_DIR, filename)
    # print(path)
    # return pd.read_csv(path)

    # df = pd.read_csv(path, dtype={'X/m': float, 'Y/m' : float, 'total_db' : float}, decimal=',')
    df = pd.read_csv(path, dtype={'X/m': float, 'Y/m' : float, 'total_db' : float})
    df.rename(columns={'total_db' : 'value'}, inplace=True)

    if all(col in df.columns for col in ["X/m", "Y/m", "value"]):
        gdf = make_geodataframe(df)
        gdf = gdf[['lat', 'lon', 'value']]
        df["value"] = df["value"].apply(classify_noise_band)
        return gdf

    return pd.DataFrame()


# 🚀 Dash app setup
app = dash.Dash(__name__)
app.title = "Timestamped Geospatial Data Viewer"

app.layout = html.Div([
    html.H2("OUTFIT"),

    html.Div([
        html.Label("Choose Date:"),
        dcc.DatePickerSingle(
            id='date-picker',
            min_date_allowed=ts_min.date(),
            max_date_allowed=ts_max.date(),
            initial_visible_month=ts_min.date(),
            date=ts_min.date()
        )
    ], style={'marginBottom': '20px'}),

    html.Div([
        # html.Label("Choose Time:"),
        dcc.Slider(0, 0, id='time-slider', step=None)
    ], style={'margin': '20px', 'padding': '20px'}),

    dcc.Store(id='filtered-timestamps'),
    dcc.Graph(id='map-graph',
              style={'width': '100%', 'height': '75vh'}
    ),
    # html.Div(id='selected-time', style={'marginTop': '50px'})
])

# 🔁 Callback 1: Filter timestamps based on selected date
@app.callback(
    Output('filtered-timestamps', 'data'),
    Output('time-slider', 'min'),
    Output('time-slider', 'max'),
    Output('time-slider', 'value'),
    Output('time-slider', 'marks'),
    Input('date-picker', 'date')
)
def update_slider_options(selected_date):
    selected_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
    matching = [ts for ts in ALL_TIMESTAMPS if ts.day == selected_date.day and ts.month == selected_date.month and ts.year == selected_date.year]
    if not matching:
        return [], 0, 0, 0, {}

    marks = {i: ts.strftime('%H:%M') for i, ts in enumerate(matching)}
    m = [ts.strftime(TS_FORMAT) for ts in matching], 0, len(matching)-1, 0, marks
    return m

# 🔁 Callback 2: Update map when time is selected
@app.callback(
    Output('map-graph', 'figure'),
    # Output('selected-time', 'children'),
    Input('time-slider', 'value'),
    State('filtered-timestamps', 'data')
)
def update_map(index, filtered_list):
    if not filtered_list:
        return px.scatter_map(), "No data"

    ts_str = filtered_list[index]
    ts = datetime.strptime(ts_str, TS_FORMAT)
    df = load_data_for_timestamp(ts)

    fig = px.scatter_map(
        df,
        lat='lat',
        lon='lon',
        color='value',
        color_discrete_map=color_map,
        range_color=[30, 90],
        hover_data=df.columns,
        zoom=14,
        center={"lat": df['lat'].mean(), "lon": df['lon'].mean()},
        # height=800,
        map_style="open-street-map"
    )
    # fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
    fig.update_layout(autosize=True)
    fig.update_traces(
        marker=dict(
            size=16,
        )
    )
    return fig

# 🏁 Run the app
if __name__ == '__main__':
    args = parse_args()
    if not os.path.isdir(args.directory):
        print(f"Invalid directory: {args.directory}")
        sys.exit(1)

    print(args.directory)

    app.run(debug=True)
