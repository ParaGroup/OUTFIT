import os
import glob
import json
import wx
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.io as pio
import imageio
from PIL import Image, ImageDraw, ImageFont
from wx.html2 import WebView
import geopandas as gpd
from shapely.geometry import Point
from functools import lru_cache
from utils import get_timestamp_from_filename

NOISE_BANDS = [
    (  40, "<40"),
    (  45, "<45"),
    (  50, "<50"),
    (  55, "<55"),
    (  60, "<60"),
    (  65, "<65"),
    (  70, "<69"),
    (  75, "<74"),
    (  80, "<80"),
    (9999, "80+")
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

LABELS = [label for _, label in NOISE_BANDS]
color_map = dict(zip(LABELS, COLOR_VALUES))

def get_rome_df():
    rome_point = Point(12.4964, 41.9028)  # Longitude, Latitude
    df = gpd.GeoDataFrame(geometry=[rome_point], crs="EPSG:4326")

    gdf = pd.DataFrame()
    gdf["lat"] = df.geometry.y
    gdf["lon"] = df.geometry.x
    gdf["z"] = [1.5]
    gdf["value"] = 75.0

    return gdf[['lat', 'lon', 'z', 'value']]

@lru_cache(maxsize=128)
def load_data_for_timestamp(filepath: str) -> pd.DataFrame:
    df = pd.read_csv(filepath)

    # if Z/m is not present, add it as 1.5
    if 'Z/m' not in df.columns:
        df['Z/m'] = "1.5"


    geometry = [Point(xy) for xy in zip(df['X/m'], df['Y/m'])]
    gdf = gpd.GeoDataFrame(df, geometry=geometry)

    # BRINDISI  EPSG:32633 WGS:8433N (UTM 33N)
    # gdf.set_crs(epsg=32633, inplace=True)
    # gdf = gdf.to_crs(epsg=4326)

    # PISA
    gdf.set_crs(epsg=3003, inplace=True)
    gdf = gdf.to_crs(epsg=4326)

    gdf["lat"] = gdf.geometry.y
    gdf["lon"] = gdf.geometry.x
    gdf["z"] = df['Z/m']
    gdf["value"] = df["total_db"]
    return gdf[['lat', 'lon', 'z', 'value']]


def get_map(df: pd.DataFrame, zoom_level, fitbounds = False) -> px.scatter_map:
    fig = px.scatter_map(
        df,
        lat='lat',
        lon='lon',
        color='value',
        color_continuous_scale=COLOR_VALUES,
        range_color=[30, 90],
        hover_data=df.columns,
        center={"lat": df['lat'].mean(), "lon": df['lon'].mean()},
        map_style="open-street-map",
    )
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        map=dict(
            # zoom = zoom_level,
            zoom = 15,
            center = dict(lat=df['lat'].mean(), lon=df['lon'].mean())
        )
    )
    fig.update_traces(
        marker=dict(
            size=6,
        )
    )
    return fig

def convert_numpy(obj):
    if isinstance(obj, dict):
        return {k: convert_numpy(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [convert_numpy(v) for v in obj]
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, (np.float32, np.float64)):
        return float(obj)
    elif isinstance(obj, (np.int32, np.int64)):
        return int(obj)
    else:
        return obj

class MapViewer(wx.Frame):

    def __init__(self, parent, title):
        super(MapViewer, self).__init__(parent, title=title, size=wx.Size(1280, 1080))

        self.panel = wx.Panel(self)

        # State
        self.folder_path = None
        self.files = []
        self.z_values = []
        self.current_time_idx = 0
        self.current_z_idx = 0
        self.zoom_level = 1

        # --- UI Components ---
        load_btn = wx.Button(self.panel, label="Load Folder")
        load_btn.Bind(wx.EVT_BUTTON, self.on_load_folder)

        self.zoom_slider = wx.Slider(self.panel, value=0, minValue=1, maxValue=20, style=wx.SL_HORIZONTAL)
        self.zoom_slider.Bind(wx.EVT_SLIDER, self.on_zoom_slider)
        self.zoom_text = wx.StaticText(self.panel, label="Zoom: 0")

        self.time_slider = wx.Slider(self.panel, value=0, minValue=0, maxValue=0, style=wx.SL_HORIZONTAL)
        self.time_slider.Bind(wx.EVT_SLIDER, self.on_time_slider)
        self.time_text = wx.StaticText(self.panel, label="Time: N/A")

        self.z_slider = wx.Slider(self.panel, value=0, minValue=0, maxValue=0, style=wx.SL_HORIZONTAL)
        self.z_slider.Bind(wx.EVT_SLIDER, self.on_z_slider)
        self.z_text = wx.StaticText(self.panel, label="Z: N/A")

        record_btn = wx.Button(self.panel, label="Record Video")
        record_btn.Bind(wx.EVT_BUTTON, self.on_record_video)

        self.status_text = wx.StaticText(self.panel, label="Status: Waiting")

        # Plotly map display in wx via WebView
        self.webview = WebView.New(self.panel)
        # rome_df = get_rome_df()
        rome_df = pd.DataFrame(columns=['lat', 'lon', 'z', 'value'])
        rome_df.loc[0] = [None, None, None, None]
        fig = get_map(rome_df, self.zoom_level)
        html = fig.to_html(include_plotlyjs='cdn')
        self.webview.SetPage(html, "")

        # Layout
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(load_btn, 0, wx.ALL | wx.EXPAND, 5)
        sizer.Add(wx.StaticText(self.panel, label="Zoom Slider:"), 0, wx.LEFT, 5)
        sizer.Add(self.zoom_slider, 0, wx.ALL | wx.EXPAND, 5)
        sizer.Add(self.zoom_text, 0, wx.ALL, 5)
        sizer.Add(wx.StaticText(self.panel, label="Time Slider:"), 0, wx.LEFT, 5)
        sizer.Add(self.time_slider, 0, wx.ALL | wx.EXPAND, 5)
        sizer.Add(self.time_text, 0, wx.ALL, 5)
        sizer.Add(wx.StaticText(self.panel, label="Z Slider:"), 0, wx.LEFT, 5)
        sizer.Add(self.z_slider, 0, wx.ALL | wx.EXPAND, 5)
        sizer.Add(self.z_text, 0, wx.ALL, 5)
        sizer.Add(self.webview, 1, wx.ALL | wx.EXPAND, 5)
        sizer.Add(record_btn, 0, wx.ALL | wx.EXPAND, 5)
        sizer.Add(self.status_text, 0, wx.ALL, 5)

        # self.zoom_slider.Bind(wx.EVT_LEFT_UP, self.on_release)
        # self.time_slider.Bind(wx.EVT_LEFT_UP, self.on_release)
        # self.z_slider.Bind(wx.EVT_LEFT_UP, self.on_release)

        self.panel.SetSizer(sizer)
        self.Centre()
        self.Show()

    # def on_release(self, event):
    #     # move focus back to the parent panel (or some neutral widget)
    #     event.GetEventObject().GetParent().SetFocus()
    #     event.Skip()

    def update_time_values(self):
        self.time_values = [os.path.basename(f) for f in self.files]
        self.time_slider.SetRange(0, len(self.time_values)-1)
        self.time_slider.SetValue(0)
        self.current_time_idx = 0
        self.update_time_text()

    def update_z_values(self, df):
        self.z_values = sorted(df['z'].astype(str).unique())
        self.z_slider.SetRange(0, len(self.z_values)-1)
        self.z_slider.SetValue(0)
        self.current_z_idx = 0
        self.update_z_text()

    def update_time_text(self):
        if self.files:
            self.time_text.SetLabel(f"Filename: {os.path.basename(self.files[self.current_time_idx])}")
        else:
            self.time_text.SetLabel("Time: N/A")

    def update_z_text(self):
        if self.z_values:
            self.z_text.SetLabel(f"Z: {self.z_values[self.current_z_idx]}")
        else:
            self.z_text.SetLabel("Z: N/A")

    def on_load_folder(self, event):
        dlg = wx.DirDialog(self, "Select a folder containing CSV files", style=wx.DD_DEFAULT_STYLE)
        if dlg.ShowModal() == wx.ID_OK:
            self.folder_path = dlg.GetPath()
            self.files = sorted(glob.glob(os.path.join(self.folder_path, "*.csv")))
            if not self.files:
                wx.MessageBox("No CSV files found in folder.", "Error", wx.ICON_ERROR)
                return

            print("ON LOAD FOLDER")
            df = load_data_for_timestamp(self.files[0])
            self.update_time_values()
            self.update_z_values(df)
            self.update_map()
        dlg.Destroy()

    def update_map(self):
        print(f"Current time idx: {self.current_time_idx}, Current z idx: {self.current_z_idx}, Zoom level: {self.zoom_level}")
        if not self.files:
            return
        print(f"Loading data from: {self.files[self.current_time_idx]}")
        df = load_data_for_timestamp(self.files[self.current_time_idx])
        print(f"Data loaded, {len(df)} rows")
        df_z = df[df['z'] == self.z_values[self.current_z_idx]]
        fig = get_map(df_z, self.zoom_level)
        fig_dict = convert_numpy(fig.to_dict())

        js_command = f"""
        Plotly.react(
            document.querySelectorAll('.plotly-graph-div')[0],
            {json.dumps(fig_dict['data'])},
            {json.dumps(fig_dict['layout'])}
        );
        """
        self.webview.RunScript(js_command)

    def on_zoom_slider(self, event):
        self.zoom_level = self.zoom_slider.GetValue()
        self.zoom_text.SetLabel(f"Zoom: {self.zoom_level}")
        self.update_map()
        event.GetEventObject().GetParent().SetFocus()
        event.Skip()


    def on_time_slider(self, event):
        self.current_time_idx = self.time_slider.GetValue()
        self.update_time_text()
        self.update_map()
        event.GetEventObject().GetParent().SetFocus()
        event.Skip()

    def on_z_slider(self, event):
        self.current_z_idx = self.z_slider.GetValue()
        self.update_z_text()
        self.update_map()
        event.GetEventObject().GetParent().SetFocus()
        event.Skip()

    def on_record_video(self, event):
        # if not self.files:
        #     wx.MessageBox("No files loaded.", "Error", wx.ICON_ERROR)
        #     return

        # self.status_text.SetLabel("Status: Recording...")
        # wx.Yield()  # update UI

        # os.makedirs("frames", exist_ok=True)
        # for i, file in enumerate(self.files):
        #     df = load_data_for_timestamp(file)
        #     df_z = df[df['z'] == self.z_values[self.current_z_idx]]
        #     fig = get_map(df_z, self.zoom_level)
        #     pio.write_image(fig, f"frames/frame_{i:03d}.png", scale=2, width=1024, height=768)

        # # Create video
        # out_file = "map_animation.mp4"
        # with imageio.get_writer(out_file, fps=2) as writer:
        #     for i in range(len(self.files)):
        #         img = imageio.imread(f"frames/frame_{i:03d}.png")
        #         writer.append_data(img)

        # self.status_text.SetLabel(f"Status: Video saved to {out_file}")
        # wx.MessageBox(f"Video saved to {out_file}", "Done", wx.ICON_INFORMATION)

        try:
            font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Helvetica.ttc", 72)
        except:
            font = ImageFont.load_default()

        out_file = "map_animation.mp4"
        writer = imageio.get_writer(
            out_file,
            fps=5,                   # frames per second
            codec="libx265",         # H.264 codec (widely compatible)
            quality=10,               # 0–10 (higher = better quality, bigger file)
            pixelformat="yuv420p",   # ensures compatibility with QuickTime/players
            ffmpeg_params=[
                "-preset", "slow",   # encoding speed/efficiency tradeoff
                "-crf", "18",        # constant rate factor (lower = higher quality)
                "-tag:v", "hvc1",     # ensures macOS QuickTime recognizes HEVC properly
            ]
        )


        with imageio.get_writer(out_file, fps=5) as writer:
            for i in range(len(self.files)):
                img = Image.open(f"frames/frame_{i:03d}.png").convert("RGBA")

                timestamp = get_timestamp_from_filename(self.files[i])
                label = timestamp.strftime("%A  %d  %H:%M")  # e.g. Monday  04  13:30

                # Draw text
                draw = ImageDraw.Draw(img)
                text_size = draw.textbbox((0, 0), label, font=font)
                text_w = text_size[2] - text_size[0]
                text_h = text_size[3] - text_size[1]

                # Position bottom-left with margin
                x, y = 20, img.height - text_h - 20

                # Background rectangle for readability
                draw.rectangle(
                    [x - 10, y - 5,     # top-left
                    x + text_w + 10,    # bottom-right
                    y + text_h + 5],    # bottom-right
                    fill=(0, 0, 0, 128))

                # Draw label
                draw.text((x, y), label, font=font, fill=(255, 255, 255, 255))

                # Convert back to numpy for imageio
                writer.append_data(imageio.core.util.asarray(img))
        self.status_text.SetLabel(f"Status: Video saved to {out_file}")
        wx.MessageBox(f"Video saved to {out_file}", "Done", wx.ICON_INFORMATION)


# -------------------------
# Run app
# -------------------------
if __name__ == "__main__":
    app = wx.App(False)
    frame = MapViewer(None, "CSV Map Viewer with Video Recording")
    app.MainLoop()
