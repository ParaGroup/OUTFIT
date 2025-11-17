import os
import sys
import argparse
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import re

color_map = {
    "35-39": "#238443",  # Moderate sea green
    "40-44": "#78C679",  # Greyish green
    "45-49": "#C2E699",  # Light greyish chartreuse green
    "50-54": "#FFFFB2",  # Pale yellow
    "55-59": "#FECC5C",  # Light brilliant amber
    "60-64": "#FD8D3C",  # Brilliant tangelo
    "65-69": "#FF0909",  # Light brilliant red
    "70-74": "#B30622",  # Moderate amaranth
    "75-79": "#67033B",  # Dark rose
    "80+":   "#1C0054",  # Deep blue violet
}

def classify_noise_band(db):
    if db < 35:
        return "less than 35"
    elif 35 <= db < 40:
        return "35-39"
    elif 40 <= db < 45:
        return "40-44"
    elif 45 <= db < 50:
        return "45-49"
    elif 50 <= db < 55:
        return "50-54"
    elif 55 <= db < 60:
        return "55-59"
    elif 60 <= db < 65:
        return "60-64"
    elif 65 <= db < 70:
        return "65-69"
    elif 70 <= db < 75:
        return "70-74"
    elif 75 <= db < 80:
        return "75-79"
    else:
        return "80+"
    

# --- Parse command-line arguments ---
def parse_args():
    parser = argparse.ArgumentParser(description="Plot dB receiver data as animated map.")
    parser.add_argument("directory", help="Directory containing CSV files")
    parser.add_argument("--zoom", type=int, default=15, help="Initial map zoom level (default: 13)")
    parser.add_argument("--output", type=str, default=None,
                        help="Optional output MP4 filename for animation (if given, saves video and exits)")
    parser.add_argument("--frame-duration", type=float, default=0.5,
                        help="Duration of each timestamp frame in seconds (default: 2)")
    return parser.parse_args()

# --- Convert EPSG:3003 to EPSG:4326 GeoDataFrame ---
# PISA
# def make_geodataframe(df):
#     geometry = [Point(xy) for xy in zip(df['X/m'], df['Y/m'])]
#     gdf = gpd.GeoDataFrame(df, geometry=geometry)
#     gdf.set_crs(epsg=3003, inplace=True)
#     gdf = gdf.to_crs(epsg=4326)
#     gdf["lon"] = gdf.geometry.x
#     gdf["lat"] = gdf.geometry.y
#     return gdf

# BRINDISI
def make_geodataframe(df):
    geometry = [Point(xy) for xy in zip(df['X/m'], df['Y/m'])]
    gdf = gpd.GeoDataFrame(df, geometry=geometry)
    gdf.set_crs(epsg=32633, inplace=True)
    gdf = gdf.to_crs(epsg=4326)
    gdf["lon"] = gdf.geometry.x
    gdf["lat"] = gdf.geometry.y
    return gdf

# --- Extract ISO timestamp from filename ---
def extract_timestamp(filename):
    match = re.search(r"\d{8}-\d{4}-[A-Za-z]+", filename)
    if match:
        try:
            dt = datetime.strptime(match.group(), "%Y%m%d-%H%M-%A")
            return dt.isoformat()
        except:
            pass
    return filename

# --- Read all CSVs and combine ---
def load_all_data(directory):
    all_data = []

    for filename in sorted(os.listdir(directory)):
        if filename.endswith(".csv"):
            path = os.path.join(directory, filename)
            df = pd.read_csv(path, dtype={'X/m': float, 'Y/m' : float, 'total_db' : float}, decimal='.')
            df.rename(columns={'total_db' : 'db'}, inplace=True)

            if all(col in df.columns for col in ["X/m", "Y/m", "db"]):
                gdf = make_geodataframe(df)
                timestamp = extract_timestamp(filename)
                gdf["timestamp"] = timestamp
                all_data.append(gdf[["lat", "lon", "db", "timestamp"]])

    if all_data:
        df = pd.concat(all_data, ignore_index=True)
        df["noise_band"] = df["db"].apply(classify_noise_band)
        return df
    else:
        return pd.DataFrame()

# --- Plot the map with Plotly ---
def plot_db_map(df, zoom):
    fig = px.scatter_map(
        df,
        lat="lat",
        lon="lon",
        color="noise_band",
        animation_frame="timestamp",
        color_discrete_map=color_map,
        zoom=zoom,
        # size_max=12,
        hover_data={"db": True},
        map_style="open-street-map",
        title="Receiver dB Levels Over Time"
    )
    fig.update_layout(margin={"r":0,"t":40,"l":0,"b":0})

    fig.update_traces(
        marker=dict(
            size=16,            # Fixed size (overrides `size=` if you want to)
            # color='red',        # Fixed color
            # opacity=0.7,
            # symbol='star/',
            # line=dict(width=2, color='black')
        )
    )

    fig.show()

    # fig = px.scatter_map(
    #     df,
    #     lat="lat",
    #     lon="lon",
    #     color="db",
    #     animation_frame="timestamp",
    #     color_continuous_scale="RdYlGr",
    #     zoom=zoom,
    #     # size_max=50,
    #     hover_data={"db": True},
    #     map_style="open-street-map",
    #     title="Receiver dB Levels Over Time"
    # )
    # fig.update_layout(margin={"r":0,"t":40,"l":0,"b":0})
    # fig.show()

# --- Save animation as MP4 using kaleido/ffmpeg ---
def save_animation_video(df, zoom, output_path, frame_duration):
    import plotly.io as pio
    import tempfile

    # Check if output exists
    if os.path.exists(output_path):
        ans = input(f"File '{output_path}' exists. Overwrite? (y/n): ").strip().lower()
        if ans != 'y':
            print("Aborted. File not overwritten.")
            sys.exit(1)

    # Plotly does not directly export animations to MP4, so export as gif then convert
    # Or use kaleido + imageio-ffmpeg pipeline

    try:
        import imageio.v2 as imageio
        import tempfile

        # Export each frame as PNG to temp dir
        tmp_dir = tempfile.mkdtemp()
        frames = []

        timestamps = sorted(df['timestamp'].unique())
        for i, ts in enumerate(timestamps):
            # Filter df for current timestamp
            df_sub = df[df['timestamp'] == ts]
            fig_sub = px.scatter_map(
                df_sub,
                lat="lat",
                lon="lon",
                color="db",
                color_continuous_scale="Turbo",
                zoom=zoom,
                hover_data={"db": True},
                map_style="open-street-map",
                title=f"Receiver dB Levels at {ts}"
            )
            fig_sub.update_layout(margin={"r":0,"t":40,"l":0,"b":0})

            # Save to PNG
            frame_path = os.path.join(tmp_dir, f"frame_{i:03d}.png")
            pio.write_image(fig_sub, frame_path, format='png', scale=2)
            frames.append(imageio.imread(frame_path))

        # Write frames to mp4
        imageio.mimsave(output_path, frames, fps=1/frame_duration)
        print(f"Video saved to {output_path}")

    except ImportError:
        print("Missing dependencies: imageio and/or ffmpeg required for video export.")
        print("Please install them via: pip install imageio[ffmpeg]")
        sys.exit(1)

# --- Main script ---
def main():
    args = parse_args()

    if not os.path.isdir(args.directory):
        print(f"Invalid directory: {args.directory}")
        sys.exit(1)

    df = load_all_data(args.directory)
    if df.empty:
        print("No valid CSV files with required columns found.")
        sys.exit(1)

    if args.output:
        # Save video and exit
        save_animation_video(df, args.zoom - 2, args.output, args.frame_duration)
    else:
        # Show interactive plot
        plot_db_map(df, args.zoom)

if __name__ == "__main__":
    main()
