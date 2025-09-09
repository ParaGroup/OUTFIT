"""
Author: Alberto Ottimo
Project: OUTFIT
Date: 2025-08-06
"""

import wx
import wx.adv
import wx.grid
import os
import re
import argparse
import pandas as pd
from datetime import datetime
from utils import *
from collect_data import collect_data
from process import *


#------------------------------------------------------------------------------
#
# Constants
#
#------------------------------------------------------------------------------

WINDOW_WIDTH  = 1024
WINDOW_HEIGHT = 768

TABLE_WINDOW_WIDTH_SPACE  = 64
TABLE_WINDOW_HEIGHT_SPACE = 64

LARGE_BUTTON_WIDTH  = 160
LARGE_BUTTON_HEIGHT = 48

FONT_SIZE    = 14
SPACER       = 16
LARGE_SPACER = 32

WINDOW_TITLE_NAME          = "OUTFIT"
DATA_COLLECTION_PANEL_NAME = "Data Collection"
PROCESSING_PANEL_NAME      = "Processing"

BROWSE_BUTTON_LABEL          = "Browse"
SHOW_BUTTON_LABEL            = "Show"
START_SCHEDULE_BUTTON_LABEL  = "Start Schedule"
REMOVE_SCHEDULE_BUTTON_LABEL = "Remove Schedule"

API_KEY_FIELDNAME         = "Api Key"
PREFIX_FIELDNAME          = "Prefix"
STREETS_FIELDNAME         = "Streets"
DATE_RANGE_FIELDNAME      = "Date Range"
DATE_FROM_FIELDNAME       = "from: "
DATE_TO_FIELDNAME         = "to: "
INTERVAL_SLIDER_FIELDNAME = "Interval (mins.)"

INTERVAL_SLIDER_MIN_VALUE  = 1
INTERVAL_SLIDER_MAX_VALUE  = 60
INTERVAL_SLIDER_INIT_VALUE = 10

ATTENUATION_MATRIX_FIELDNAME = "Attenuation Matrix"
STREET_PARAMS_FIELDNAME      = "Street Params"
FREQ_COEFFS_FIELDNAME        = "Freq. Coeffs."
CURVE_A_FIELDNAME            = "Curve A"
VEHICLE_FIELDNAME           = "Vehicle"


#------------------------------------------------------------------------------
#
# Data functions
#
#------------------------------------------------------------------------------

def get_timestamp_str_from_date_time(date, time) -> str:
    date_str = date.FormatISODate()
    time_str = time.Format("%H:%M:%S")
    return f"{date_str} {time_str}"

def wxDateTime_to_datetime(dt: wx.DateTime) -> datetime:
    if not dt.IsValid():
        raise ValueError("Invalid wx.DateTime object")

    year = int(dt.GetYear())
    month = int(dt.GetMonth()) + 1  # wx.DateTime months are 0-based
    day = int(dt.GetDay())
    hour = int(dt.GetHour())
    minute = int(dt.GetMinute())
    second = int(dt.GetSecond())

    return datetime(year, month, day, hour, minute, second)

def datetime_to_wxDateTime(dt: datetime) -> wx.DateTime:
    print(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)

    return wx.DateTime(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)

def get_datetime_from_str(timestamp_str) -> datetime:
    if timestamp_str:
        return datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
    return datetime.now()

def get_wxDateTime_from_str(timestamp_str) -> wx.DateTime:
    dt = get_datetime_from_str(timestamp_str)
    return datetime_to_wxDateTime(dt)


#------------------------------------------------------------------------------
#
# CSV Utility functions
#
#------------------------------------------------------------------------------

class CSVViewer(wx.Frame):
    def __init__(self, parent: wx.Window, df: pd.DataFrame, path: str):
        super().__init__(parent, title=os.path.basename(path))

        self.df = df
        self.grid = wx.grid.Grid(self)
        self.grid.CreateGrid(len(df), len(df.columns))
        for col_idx, col_name in enumerate(df.columns):
            self.grid.SetColLabelValue(col_idx, col_name)
            for row_idx, value in enumerate(df[col_name]):
                self.grid.SetCellValue(row_idx, col_idx, str(value))

        self.grid.AutoSizeColumns()

        self.grid.Fit()
        self.Fit()

        display = wx.Display(wx.Display.GetFromWindow(self))
        geometry = display.GetGeometry()
        max_width, max_height = geometry.GetWidth(), geometry.GetHeight() - TABLE_WINDOW_HEIGHT_SPACE

        w, h = self.GetSize()
        self.SetSize(min(w + TABLE_WINDOW_WIDTH_SPACE, max_width), min(h, max_height))
        self.Center()


def on_file_browse(window, field, default_dir=""):
    dlg = wx.FileDialog(window, message="Choose a CSV file",
                        defaultDir=default_dir,
                        style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
    if dlg.ShowModal() == wx.ID_OK:
        path = dlg.GetPath()
        try:
            if re.search(r'\.(csv|parquet)$', path, re.IGNORECASE) or re.search(r'\.part\d+$', path, re.IGNORECASE):
                field.SetValue(path)
            else:
                wx.MessageBox(
                    "File must be .csv, .parquet, or .part*",
                    "Unsupported file",
                    wx.OK | wx.ICON_ERROR,
                    parent=window
                )
        finally:
            dlg.Destroy()


def on_file_show(window, field):
    path = field.GetValue()
    try:
        df = read_file(path)
        logging.info(f"Loaded data file: {path}")
    except Exception as e:
        logging.error(f"Failed to load data file {path}: {e}")
        wx.MessageBox(f"Failed to load data file {path}: {e}", "Error", wx.OK | wx.ICON_ERROR)
        return

    tableViewer = CSVViewer(window, df, path)
    tableViewer.Show()

def control_name_str(name: str) -> str:
    return name.lower().replace('.', '').replace(' ', '_')

def control_name_label(name: str) -> str:
    return f"{control_name_str(name)}_label"

def control_name_field(name: str) -> str:
    return f"{control_name_str(name)}_field"

def control_name_browse_button(name: str) -> str:
    return f"{control_name_str(name)}_browse_button"

def control_name_show_button(name: str) -> str:
    return f"{control_name_str(name)}_show_button"

def control_name_sizer(name: str) -> str:
    return f"{control_name_str(name)}_sizer"

def add_csv_field(window, form_sizer, font, label, field_evt, browse_evt, show_evt):
    _label = wx.StaticText(window, label=label)
    _label.SetFont(font)

    _field = wx.TextCtrl(window, style=wx.TE_PROCESS_ENTER)
    _field.SetFont(font)
    _field.Bind(wx.EVT_TEXT, field_evt)

    _browse_button = wx.Button(window, label=BROWSE_BUTTON_LABEL)
    _browse_button.SetFont(font)
    _browse_button.Bind(wx.EVT_BUTTON, browse_evt)

    _show_button = None
    if show_evt:
        _show_button = wx.Button(window, label=SHOW_BUTTON_LABEL)
        _show_button.SetFont(font)
        _show_button.Bind(wx.EVT_BUTTON, show_evt)

    _sizer = wx.BoxSizer(wx.HORIZONTAL)
    _sizer.Add(_field, 1, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, SPACER)
    _sizer.Add(_browse_button, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, SPACER)

    if _show_button:
        _sizer.Add(_show_button, 0, wx.ALIGN_CENTER_VERTICAL)

    setattr(window, control_name_label(label), _label)
    setattr(window, control_name_field(label), _field)
    setattr(window, control_name_browse_button(label), _browse_button)

    if _show_button:
        setattr(window, control_name_show_button(label), _show_button)

    setattr(window, control_name_sizer(label), _sizer)

    form_sizer.Add(_label, 0, wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
    form_sizer.Add(_sizer, 1, wx.EXPAND)


#------------------------------------------------------------------------------
#
# Panel functions
#
#------------------------------------------------------------------------------

def toggle_enable_sizer(sizer, enable=True, gray_label=True):
    for item in sizer.GetChildren():
        win = item.GetWindow()
        if win:
            win.Enable(enable)
        elif item.IsSizer():
            child_sizer = item.GetSizer()
            if child_sizer:
                toggle_enable_sizer(child_sizer, enable, gray_label)


class DataCollectionPanel(wx.Panel):
    def __init__(self, parent: wx.Window, font: wx.Font):
        super().__init__(parent)
        self.last_dir = os.getcwd()
        self.font = font

        # Custom label (instead of relying on StaticBox's built-in one)
        self.title = wx.StaticText(self, label=DATA_COLLECTION_PANEL_NAME)
        self.title.SetFont(self.font)

        # StaticBox without label
        self.box = wx.StaticBox(self)
        self.box_sizer = wx.StaticBoxSizer(self.box, wx.VERTICAL)

        # Form inside the box
        self.form_sizer = wx.FlexGridSizer(rows=0, cols=2, hgap=FONT_SIZE, vgap=FONT_SIZE)
        self.form_sizer.AddGrowableCol(1, 1)

        # API KEY
        self.api_key_label = wx.StaticText(self, label=API_KEY_FIELDNAME)
        self.api_key_label.SetFont(self.font)

        self.api_key_field = wx.TextCtrl(self, style=wx.TE_PROCESS_ENTER)
        self.api_key_field.SetFont(self.font)

        self.form_sizer.Add(self.api_key_label, 0, wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        self.form_sizer.Add(self.api_key_field, 1, wx.EXPAND)

        # PREFIX
        self.prefix_label = wx.StaticText(self, label=PREFIX_FIELDNAME)
        self.prefix_label.SetFont(self.font)

        self.prefix_field = wx.TextCtrl(self, style=wx.TE_PROCESS_ENTER)
        self.prefix_field.SetFont(self.font)

        self.form_sizer.Add(self.prefix_label, 0, wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        self.form_sizer.Add(self.prefix_field, 1, wx.EXPAND)

        # STREETS
        add_csv_field(self, self.form_sizer, self.font, STREETS_FIELDNAME, self.on_streets_field_change, self.on_streets_browse, self.on_streets_show)

        # DATE
        self.date_label = wx.StaticText(self, label=DATE_RANGE_FIELDNAME)
        self.date_label.SetFont(font)

        self.from_label = wx.StaticText(self, label=DATE_FROM_FIELDNAME)
        self.from_label.SetFont(font)

        self.start_time = wx.adv.TimePickerCtrl(self)
        self.start_time.SetFont(font)

        self.start_date = wx.adv.DatePickerCtrl(self, style=wx.adv.DP_DROPDOWN)
        self.start_date.SetFont(font)

        self.to_label = wx.StaticText(self, label=DATE_TO_FIELDNAME)
        self.to_label.SetFont(font)

        self.end_time = wx.adv.TimePickerCtrl(self)
        self.end_time.SetFont(font)

        self.end_date = wx.adv.DatePickerCtrl(self, style=wx.adv.DP_DROPDOWN)
        self.end_date.SetFont(font)

        self.date_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.date_sizer.Add(self.from_label, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, SPACER)
        self.date_sizer.Add(self.start_time, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, SPACER)
        self.date_sizer.Add(self.start_date, 0, wx.RIGHT, SPACER)
        self.date_sizer.Add(self.to_label, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, SPACER)
        self.date_sizer.Add(self.end_time, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, SPACER)
        self.date_sizer.Add(self.end_date, 0)

        self.form_sizer.Add(self.date_label, 0, wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        self.form_sizer.Add(self.date_sizer, 1, wx.EXPAND)

        # INTERVAL
        self.interval_label = wx.StaticText(self, label=INTERVAL_SLIDER_FIELDNAME)
        self.interval_label.SetFont(font)

        self.interval_field = wx.TextCtrl(self, value=f'{INTERVAL_SLIDER_INIT_VALUE}', size=wx.Size(50, -1))
        self.interval_field.SetFont(font)
        self.interval_field.Bind(wx.EVT_TEXT, self.on_interval_field_change)

        self.interval_slider = wx.Slider(self, value=INTERVAL_SLIDER_INIT_VALUE, minValue=1, maxValue=60, style=wx.SL_HORIZONTAL | wx.SL_MIN_MAX_LABELS)
        self.interval_slider.SetFont(font)
        self.interval_slider.Bind(wx.EVT_SLIDER, self.on_interval_slider_change)

        self.interval_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.interval_sizer.Add(self.interval_field, 0, wx.ALIGN_CENTER_VERTICAL, SPACER)
        self.interval_sizer.AddSpacer(SPACER)
        self.interval_sizer.Add(self.interval_slider, 1, wx.RIGHT)

        self.form_sizer.Add(self.interval_label, 0, wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL)
        self.form_sizer.Add(self.interval_sizer, 1, wx.EXPAND)

        self.box_sizer.Add(self.form_sizer, 1, wx.EXPAND | wx.ALL, SPACER)
        self.outer_sizer = wx.BoxSizer(wx.VERTICAL)
        self.outer_sizer.Add(self.title, 0, wx.LEFT | wx.TOP, SPACER)
        self.outer_sizer.Add(self.box_sizer, 1, wx.EXPAND | wx.ALL, SPACER)
        self.SetSizer(self.outer_sizer)

    def on_interval_slider_change(self, event):
        val = str(self.interval_slider.GetValue())
        self.interval_field.ChangeValue(val)

    def on_interval_field_change(self, event):
        val = self.interval_field.GetValue()
        if val.isdigit():
            val_int = int(val)
            if INTERVAL_SLIDER_MIN_VALUE <= val_int <= INTERVAL_SLIDER_MAX_VALUE:
                self.interval_slider.SetValue(val_int)

    def on_streets_field_change(self, event):
        path = getattr(self, "streets_field", None).GetValue()
        self.last_dir = os.path.dirname(path)

    def on_streets_browse(self, event):
        field = getattr(self, "streets_field", None)
        on_file_browse(self, field, self.last_dir)

    def on_streets_show(self, event):
        field = getattr(self, "streets_field", None)
        on_file_show(self, field)

    def toggle_date_range(self, enable=True):
        toggle_enable_sizer(self.date_sizer, enable)

class ProcessingPanel(wx.Panel):
    def __init__(self, parent, font):
        super().__init__(parent)
        self.last_dir = os.getcwd()
        self.font = font

        # Custom label (instead of relying on StaticBox's built-in one)
        self.processing_checkbox = wx.CheckBox(self, label=PROCESSING_PANEL_NAME)
        self.processing_checkbox.SetFont(self.font)
        self.processing_checkbox.Bind(wx.EVT_CHECKBOX, self.on_toggle_processing)

        # StaticBox without label
        self.box = wx.StaticBox(self)
        self.box_sizer = wx.StaticBoxSizer(self.box, wx.VERTICAL)

        # Form inside the box
        self.form_sizer = wx.FlexGridSizer(rows=0, cols=2, hgap=FONT_SIZE, vgap=FONT_SIZE)
        self.form_sizer.AddGrowableCol(1, 1)

        add_csv_field(self, self.form_sizer, self.font, ATTENUATION_MATRIX_FIELDNAME, self.on_attenuation_matrix_field_change, self.on_attenuation_matrix_browse, self.on_attenuation_matrix_show)
        add_csv_field(self, self.form_sizer, self.font, STREET_PARAMS_FIELDNAME, self.on_street_params_field_change, self.on_street_params_browse, self.on_street_params_show)
        add_csv_field(self, self.form_sizer, self.font, FREQ_COEFFS_FIELDNAME, self.on_freq_coeffs_field_change, self.on_freq_coeffs_browse, self.on_freq_coeffs_show)
        add_csv_field(self, self.form_sizer, self.font, CURVE_A_FIELDNAME, self.on_curve_a_field_change, self.on_curve_a_browse, self.on_curve_a_show)
        add_csv_field(self, self.form_sizer, self.font, VEHICLE_FIELDNAME, self.on_vehicle_field_change, self.on_vehicle_browse, None)

        # Checkbox for enabling/disabling merge
        self.merge_checkbox = wx.CheckBox(self, label="Output results into a single file")
        self.merge_checkbox.SetFont(self.font)

        self.form_sizer.Add(self.merge_checkbox, 0, wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL)

        self.box_sizer.Add(self.form_sizer, 1, wx.EXPAND | wx.ALL, SPACER)
        self.outer_sizer = wx.BoxSizer(wx.VERTICAL)
        self.outer_sizer.Add(self.processing_checkbox, 0, wx.LEFT | wx.TOP, SPACER)
        self.outer_sizer.Add(self.box_sizer, 1, wx.EXPAND | wx.ALL, SPACER)
        self.SetSizer(self.outer_sizer)

    def on_toggle_processing(self, event):
        enabled = self.processing_checkbox.IsChecked()
        toggle_enable_sizer(self.box_sizer, enabled)

    def on_attenuation_matrix_field_change(self, event):
        path = getattr(self, control_name_field(ATTENUATION_MATRIX_FIELDNAME), None).GetValue()
        self.last_dir = os.path.dirname(path)

    def on_attenuation_matrix_browse(self, event):
        field = getattr(self, control_name_field(ATTENUATION_MATRIX_FIELDNAME), None)
        on_file_browse(self, field, self.last_dir)

    def on_attenuation_matrix_show(self, event):
        field = getattr(self, control_name_field(ATTENUATION_MATRIX_FIELDNAME), None)
        on_file_show(self, field)

    def on_street_params_field_change(self, event):
        path = getattr(self, control_name_field(STREET_PARAMS_FIELDNAME), None).GetValue()
        self.last_dir = os.path.dirname(path)

    def on_street_params_browse(self, event):
        field = getattr(self, control_name_field(STREET_PARAMS_FIELDNAME), None)
        on_file_browse(self, field, self.last_dir)

    def on_street_params_show(self, event):
        field = getattr(self, control_name_field(STREET_PARAMS_FIELDNAME), None)
        on_file_show(self, field)

    def on_freq_coeffs_field_change(self, event):
        path = getattr(self, control_name_field(FREQ_COEFFS_FIELDNAME), None).GetValue()
        self.last_dir = os.path.dirname(path)

    def on_freq_coeffs_browse(self, event):
        field = getattr(self, control_name_field(FREQ_COEFFS_FIELDNAME), None)
        on_file_browse(self, field, self.last_dir)

    def on_freq_coeffs_show(self, event):
        field = getattr(self, control_name_field(FREQ_COEFFS_FIELDNAME), None)
        on_file_show(self, field)

    def on_curve_a_field_change(self, event):
        path = getattr(self, control_name_field(CURVE_A_FIELDNAME), None).GetValue()
        self.last_dir = os.path.dirname(path)

    def on_curve_a_browse(self, event):
        field = getattr(self, control_name_field(CURVE_A_FIELDNAME), None)
        on_file_browse(self, field, self.last_dir)

    def on_curve_a_show(self, event):
        field = getattr(self, control_name_field(CURVE_A_FIELDNAME), None)
        on_file_show(self, field)

    def on_vehicle_field_change(self, event):
        path = getattr(self, control_name_field(VEHICLE_FIELDNAME), None).GetValue()
        self.last_dir = os.path.dirname(path)

    def on_vehicle_browse(self, event):
        field = getattr(self, control_name_field(VEHICLE_FIELDNAME), None)
        on_file_browse(self, field, self.last_dir)


#------------------------------------------------------------------------------
#
# Main Frame
#
#------------------------------------------------------------------------------

class SchedulerFrame(wx.Frame):
    def __init__(self):
        super().__init__(None, title=WINDOW_TITLE_NAME)

        self.last_dir = os.getcwd()
        self.font = wx.Font(FONT_SIZE, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)

        self.panel = wx.Panel(self)
        self.Bind(wx.EVT_CLOSE, self.on_close)
        self.Bind(wx.EVT_SHOW, self.on_open)

        self.main_sizer = wx.BoxSizer(wx.VERTICAL)
        self.dataCollectionPanel = DataCollectionPanel(self.panel, self.font)
        self.processingPanel = ProcessingPanel(self.panel, self.font)

        self.start_schedule_button = wx.Button(self.panel, label=START_SCHEDULE_BUTTON_LABEL)
        self.start_schedule_button.SetFont(self.font)
        self.start_schedule_button.SetMinSize(wx.Size(LARGE_BUTTON_WIDTH, LARGE_BUTTON_HEIGHT))
        self.start_schedule_button.Bind(wx.EVT_BUTTON, self.on_start_schedule)

        self.remove_schedules_button = wx.Button(self.panel, label=REMOVE_SCHEDULE_BUTTON_LABEL)
        self.remove_schedules_button.SetFont(self.font)
        self.remove_schedules_button.SetMinSize(wx.Size(LARGE_BUTTON_WIDTH, LARGE_BUTTON_HEIGHT))
        self.remove_schedules_button.Bind(wx.EVT_BUTTON, self.on_cancel_schedule)

        self.buttons_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.buttons_sizer.Add(self.start_schedule_button, 1, wx.ALL | wx.EXPAND, SPACER)
        self.buttons_sizer.Add(self.remove_schedules_button, 1, wx.ALL | wx.EXPAND, SPACER)

        self.main_sizer.Add(self.dataCollectionPanel, 0, wx.ALL | wx.EXPAND)
        self.main_sizer.Add(self.processingPanel, 0, wx.ALL | wx.EXPAND)
        self.main_sizer.Add(self.buttons_sizer, 0, wx.EXPAND)

        self.outer_sizer = wx.BoxSizer(wx.VERTICAL)
        self.outer_sizer.Add(self.main_sizer, 1, wx.ALL | wx.EXPAND, border=SPACER)
        self.panel.SetSizer(self.outer_sizer)
        self.Layout()

        self.main_sizer.Fit(self)
        current_size = self.GetSize()
        self.SetSize(wx.Size(WINDOW_WIDTH, current_size.height))
        self.Center()

    def load_env(self):
        try:
            env = EnvManager()
            api_key = f'{env.get(Env.API_KEY)}'
            prefix = f'{env.get(Env.PREFIX)}'
            streets = f'{env.get(Env.STREETS_FILEPATH)}'
            ts_from_str = f'{env.get(Env.TIMESTAMP_FROM)}'
            ts_to_str = f'{env.get(Env.TIMESTAMP_TO)}'
            ts_from = get_datetime_from_str(ts_from_str)
            ts_to = get_datetime_from_str(ts_to_str)
            interval = f'{env.get(Env.INTERVAL, INTERVAL_SLIDER_INIT_VALUE)}'

            process_enabled_default = False
            street_params_default = os.path.join(PARAMS_DIR, STREET_PARAMS_FILENAME)
            freq_coeffs_default = os.path.join(PARAMS_DIR, FREQ_COEFFS_FILENAME)
            curve_a_default = os.path.join(PARAMS_DIR, CURVE_A_FILENAME)
            merge_default = False

            process_enabled = env.get_bool(Env.PROCESS_DATA, process_enabled_default)
            attenuation_matrix = f'{env.get(Env.ATTENUATION_MATRIX)}'
            street_params = f'{env.get(Env.STREET_PARAMS, street_params_default)}'
            freq_coeffs = f'{env.get(Env.FREQ_COEFFS, freq_coeffs_default)}'
            curve_a = f'{env.get(Env.CURVE_A, curve_a_default)}'
            vehicles = f'{env.get(Env.VEHICLES)}'
            merge = env.get_bool(Env.MERGE, merge_default)

            self.dataCollectionPanel.api_key_field.SetValue(api_key)
            self.dataCollectionPanel.prefix_field.SetValue(prefix)
            getattr(self.dataCollectionPanel, control_name_field(STREETS_FIELDNAME)).SetValue(streets)
            self.dataCollectionPanel.start_date.SetValue(ts_from)
            self.dataCollectionPanel.start_time.SetValue(ts_from)
            self.dataCollectionPanel.end_date.SetValue(ts_to)
            self.dataCollectionPanel.end_time.SetValue(ts_to)
            self.dataCollectionPanel.interval_field.SetValue(interval)

            self.processingPanel.processing_checkbox.SetValue(process_enabled)
            getattr(self.processingPanel, control_name_field(ATTENUATION_MATRIX_FIELDNAME)).SetValue(attenuation_matrix)
            getattr(self.processingPanel, control_name_field(STREET_PARAMS_FIELDNAME)).SetValue(street_params)
            getattr(self.processingPanel, control_name_field(FREQ_COEFFS_FIELDNAME)).SetValue(freq_coeffs)
            getattr(self.processingPanel, control_name_field(CURVE_A_FIELDNAME)).SetValue(curve_a)
            getattr(self.processingPanel, control_name_field(VEHICLE_FIELDNAME)).SetValue(vehicles)
            self.processingPanel.merge_checkbox.SetValue(merge)

            logging.info("Environment variables loaded successfully.")
        except Exception as e:
            logging.error(f"Failed to load environment variables: {e}")

    def store_env(self, filename: str = ".env"):
        try:
            api_key = self.dataCollectionPanel.api_key_field.GetValue()
            prefix = self.dataCollectionPanel.prefix_field.GetValue()
            streets = getattr(self.dataCollectionPanel, control_name_field(STREETS_FIELDNAME)).GetValue()
            time_from = self.dataCollectionPanel.start_time.GetValue()
            date_from = self.dataCollectionPanel.start_date.GetValue()
            time_to = self.dataCollectionPanel.end_time.GetValue()
            date_to = self.dataCollectionPanel.end_date.GetValue()
            ts_from_str = get_timestamp_str_from_date_time(date_from, time_from)
            ts_to_str = get_timestamp_str_from_date_time(date_to, time_to)
            interval = self.dataCollectionPanel.interval_field.GetValue()
            process_data = self.processingPanel.processing_checkbox.GetValue()
            attenuation_matrix = getattr(self.processingPanel, control_name_field(ATTENUATION_MATRIX_FIELDNAME)).GetValue()
            street_params = getattr(self.processingPanel, control_name_field(STREET_PARAMS_FIELDNAME)).GetValue()
            freq_coeffs = getattr(self.processingPanel, control_name_field(FREQ_COEFFS_FIELDNAME)).GetValue()
            curve_a = getattr(self.processingPanel, control_name_field(CURVE_A_FIELDNAME)).GetValue()
            vehicles = getattr(self.processingPanel, control_name_field(VEHICLE_FIELDNAME)).GetValue()
            merge = self.processingPanel.merge_checkbox.GetValue()

            env = EnvManager(filename)
            env.set(Env.API_KEY, api_key)
            env.set(Env.PREFIX, prefix)
            env.set(Env.STREETS_FILEPATH, streets)
            env.set(Env.TIMESTAMP_FROM, ts_from_str)
            env.set(Env.TIMESTAMP_TO, ts_to_str)
            env.set(Env.INTERVAL, interval)
            env.set_bool(Env.PROCESS_DATA, process_data)
            env.set(Env.ATTENUATION_MATRIX, attenuation_matrix)
            env.set(Env.STREET_PARAMS, street_params)
            env.set(Env.FREQ_COEFFS, freq_coeffs)
            env.set(Env.CURVE_A, curve_a)
            env.set(Env.VEHICLES, vehicles)
            env.set_bool(Env.MERGE, merge)

            logging.info(f"Environment variables stored to {filename}")
        except Exception as e:
            logging.error(f"Failed to store environment variables: {e}")

    def on_open(self, event):
        if event.IsShown():
            self.load_env()
            self.dataCollectionPanel.toggle_date_range(is_windows())
            self.processingPanel.on_toggle_processing(None)

        event.Skip()

    def on_close(self, event):
        self.store_env()
        self.Destroy()

    def on_start_schedule(self, event):
        try:
            # api_key = self.dataCollectionPanel.api_key_field.GetValue()
            prefix = self.dataCollectionPanel.prefix_field.GetValue()
            streets = getattr(self.dataCollectionPanel, control_name_field(STREETS_FIELDNAME)).GetValue()
            time_from = self.dataCollectionPanel.start_time.GetValue()
            date_from = self.dataCollectionPanel.start_date.GetValue()
            time_to = self.dataCollectionPanel.end_time.GetValue()
            date_to = self.dataCollectionPanel.end_date.GetValue()
            interval = self.dataCollectionPanel.interval_slider.GetValue()
            process_data = self.processingPanel.processing_checkbox.GetValue()
            attenuation_matrix = getattr(self.processingPanel, control_name_field(ATTENUATION_MATRIX_FIELDNAME)).GetValue()
            street_params = getattr(self.processingPanel, control_name_field(STREET_PARAMS_FIELDNAME)).GetValue()
            freq_coeffs = getattr(self.processingPanel, control_name_field(FREQ_COEFFS_FIELDNAME)).GetValue()
            curve_a = getattr(self.processingPanel, control_name_field(CURVE_A_FIELDNAME)).GetValue()
            vehicles = getattr(self.processingPanel, control_name_field(VEHICLE_FIELDNAME)).GetValue()

            start_time = wxDateTime_to_datetime(time_from)
            start_date = wxDateTime_to_datetime(date_from)
            end_time = wxDateTime_to_datetime(time_to)
            end_date = wxDateTime_to_datetime(date_to)

            start_dt = datetime(start_date.year, start_date.month, start_date.day,
                                start_time.hour, start_time.minute)
            end_dt = datetime(end_date.year, end_date.month, end_date.day,
                            end_time.hour, end_time.minute)

            env_filepath = f'{prefix}_{start_dt.strftime("%Y%m%d-%H%M")}.env'
            env_abs_filepath = os.path.abspath(env_filepath)

            self.store_env()
            self.store_env(env_filepath)

            if start_dt < datetime.now():
                logging.warning("Start datetime is in the past.")
                wx.MessageBox("Start date and time should be after the current date and time!", "Error", wx.ICON_ERROR)
                return

            if end_dt <= start_dt:
                logging.warning("Start datetime is not earlier than end datetime.")
                wx.MessageBox("Start datetime should be earlier than end datetime!", "Error", wx.ICON_ERROR)
                return

            if not os.path.isfile(streets):
                logging.error(f"Data filepath does not exist: {streets}")
                wx.MessageBox("Data filepath is not correct!", "Error", wx.ICON_ERROR)
                return

            if process_data:
                if not os.path.isfile(attenuation_matrix):
                    parts = get_part_filenames(attenuation_matrix)
                    if not parts:
                        logging.error(f"Data filepath does not exist: {attenuation_matrix}")
                        wx.MessageBox("Data filepath is not correct!", "Error", wx.ICON_ERROR)
                        return

                if not os.path.isfile(street_params):
                    logging.error(f"Data filepath does not exist: {street_params}")
                    wx.MessageBox("Data filepath is not correct!", "Error", wx.ICON_ERROR)
                    return

                if not os.path.isfile(freq_coeffs):
                    logging.error(f"Data filepath does not exist: {freq_coeffs}")
                    wx.MessageBox("Data filepath is not correct!", "Error", wx.ICON_ERROR)
                    return

                if not os.path.isfile(curve_a):
                    logging.error(f"Data filepath does not exist: {curve_a}")
                    wx.MessageBox("Data filepath is not correct!", "Error", wx.ICON_ERROR)
                    return

            exe_filepath = sys.executable
            if not os.path.isfile(exe_filepath):
                logging.error("Python executable not found.")
                wx.MessageBox("Internal error!", "Error", wx.ICON_ERROR)
                return

            schedule_script(
                exe_filepath,
                ['--env', env_abs_filepath],
                start_dt,
                end_dt,
                interval
            )
            logging.info(f"Task scheduled from {start_dt} to {end_dt}, interval={interval} minutes.")
            wx.MessageBox("Task Scheduled!", "Info")
        except Exception as e:
            logging.error(f"Error while inserting schedule: {e}")
            wx.MessageBox("Error while inserting schedule!", "Error", wx.ICON_ERROR)

    def on_cancel_schedule(self, event):
        try:
            remove_schedule()
            env_files = [f for f in os.listdir('.') if f.endswith('.env') and f != '.env']
            for env_file in env_files:
                os.remove(env_file)
                logging.info(f"Deleted environment file: {env_file}")

            logging.info("All schedules removed successfully.")
            wx.MessageBox("Schedule(s) removed!", "Info", wx.ICON_INFORMATION)
        except Exception as e:
            logging.error(f"Error while removing schedule(s): {e}")
            wx.MessageBox("Error while removing schedule!", "Error", wx.ICON_ERROR)


#------------------------------------------------------------------------------
#
# Main Functions
#
#------------------------------------------------------------------------------

def parse_args():
    """
    Parse command-line arguments.
    """
    parser = argparse.ArgumentParser(description="")
    parser.add_argument('--env', required=False,  help="Execute the actual data collection.")
    return parser.parse_args()

def execute_collect_data(env_filepath: str = ".env"):
    try:
        now = datetime.now()
        env = EnvManager(env_filepath)
        api_key = str(env.get(Env.API_KEY))
        prefix = str(env.get(Env.PREFIX))
        streets_filepath = str(env.get(Env.STREETS_FILEPATH))
        streets_dirname = os.path.dirname(streets_filepath)
        collected_data_dirpath = get_api_output_dirpath(streets_dirname)
        processed_data_dirpath = get_processed_data_dirpath(streets_dirname)
        processed_data_filepath = generate_output_filename(processed_data_dirpath, prefix, now)

        process_enabled_default = False
        street_params_default = os.path.join(PARAMS_DIR, STREET_PARAMS_FILENAME)
        freq_coeffs_default = os.path.join(PARAMS_DIR, FREQ_COEFFS_FILENAME)
        curve_a_default = os.path.join(PARAMS_DIR, CURVE_A_FILENAME)
        merge_default = False

        process_enabled = env.get_bool(Env.PROCESS_DATA, process_enabled_default)
        attenuation_matrix = f'{env.get(Env.ATTENUATION_MATRIX)}'
        street_params = f'{env.get(Env.STREET_PARAMS, street_params_default)}'
        freq_coeffs = f'{env.get(Env.FREQ_COEFFS, freq_coeffs_default)}'
        curve_a = f'{env.get(Env.CURVE_A, curve_a_default)}'
        vehicles_dirpath = f'{env.get(Env.VEHICLES)}'
        merge = env.get_bool(Env.MERGE, merge_default)

        if not os.path.isdir(collected_data_dirpath):
            os.mkdir(collected_data_dirpath)
            logging.info(f"Created output directory: {collected_data_dirpath}")

        logging.info(f"Collecting data with prefix={prefix}, input={streets_filepath}, output={collected_data_dirpath}")
        collected_data_filepath = collect_data(api_key, streets_filepath, collected_data_dirpath, prefix, now)

        if process_enabled:
            if not os.path.isdir(processed_data_dirpath):
                os.mkdir(processed_data_dirpath)
                logging.info(f"Created processed data directory: {processed_data_dirpath}")

            if re.search(r'\.part\d+$', attenuation_matrix, re.IGNORECASE):
                attenuation_matrix = replace_extension(attenuation_matrix, ".parquet")
                logging.info(f"Using attenuation matrix file: {attenuation_matrix}")

            if vehicles_dirpath and not os.path.isdir(vehicles_dirpath):
                os.makedirs(vehicles_dirpath)
                logging.info(f"Created vehicles directory: {vehicles_dirpath}")

            logging.info(f"Processing data with input={collected_data_filepath}, output={processed_data_filepath}, vehicles={vehicles_dirpath}")
            pipeline = Pipeline(attenuation_matrix,
                    street_params,
                    freq_coeffs,
                    curve_a)
            pipeline.execute(collected_data_filepath, processed_data_filepath, vehicles_dirpath, merge_default)

        return now
    except Exception as e:
        logging.error(f"Data collection failed: {e}")
        raise

if __name__ == "__main__":
    now = datetime.now()

    args = parse_args()
    is_env = args.env is not None
    setup_logging('collect_gui', now, to_file=(not is_env))

    if is_env:
        try:
            data_now = execute_collect_data(args.env)
        except Exception as e:
            logging.error(f"Data collection execution failed: {e}")

    else:
        app = wx.App(False)
        frame = SchedulerFrame()
        frame.Show()
        app.MainLoop()