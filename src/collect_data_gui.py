"""
Authors: Alberto Ottimo
Project: OUTFIT
Date: 2025-08-06
"""

import wx
import wx.adv
import wx.grid
import os
import argparse
import pandas as pd
from datetime import datetime
from utils import *
from collect_data import collect_data

INITIAL_SLIDER_VALUE = 10


def get_datetime_from_str(timestamp_str):
    if timestamp_str:
        return datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
    return datetime.now()

def get_timestamp_str_from_date_time(date, time):
    date_str = date.FormatISODate()
    time_str = time.Format("%H:%M:%S")
    return f"{date_str} {time_str}"


class SchedulerFrame(wx.Frame):
    def __init__(self):
        super().__init__(None, title="OUTFIT", size=(1024, 768))
        self.Bind(wx.EVT_CLOSE, self.on_close)
        self.Bind(wx.EVT_SHOW, self.on_open)

        self.panel = wx.Panel(self)
        self.last_dir = os.getcwd()

        font_size = 16
        font = wx.Font(font_size, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        form_sizer = wx.FlexGridSizer(rows=0, cols=2, hgap=font_size, vgap=font_size)
        form_sizer.AddGrowableCol(1, 1)

        # API Key
        api_label = wx.StaticText(self.panel, label="API KEY")
        api_label.SetFont(font)
        form_sizer.Add(api_label, 0, wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL)
        self.api_txt = wx.TextCtrl(self.panel, style=wx.TE_PROCESS_ENTER)
        self.api_txt.SetFont(font)
        form_sizer.Add(self.api_txt, 1, wx.EXPAND)

        # Prefix
        prefix_label = wx.StaticText(self.panel, label="Prefix")
        prefix_label.SetFont(font)
        form_sizer.Add(prefix_label, 0, wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL)
        self.prefix_txt = wx.TextCtrl(self.panel)
        self.prefix_txt.SetFont(font)
        form_sizer.Add(self.prefix_txt, 1, wx.EXPAND)

        # Data File Input with Browse
        data_label = wx.StaticText(self.panel, label="Data")
        data_label.SetFont(font)
        form_sizer.Add(data_label, 0, wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL)
        data_input_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.data_txt = wx.TextCtrl(self.panel)
        self.data_txt.SetFont(font)
        self.data_txt.Bind(wx.EVT_TEXT, self.on_data_txt_change)
        data_input_sizer.Add(self.data_txt, 1, wx.RIGHT, 5)
        browse_btn = wx.Button(self.panel, label="Browse")
        browse_btn.SetFont(font)
        browse_btn.Bind(wx.EVT_BUTTON, self.on_browse)
        data_input_sizer.Add(browse_btn, 0)
        form_sizer.Add(data_input_sizer, 1, wx.EXPAND | wx.ALIGN_CENTER_VERTICAL)

        # Start & End Date
        if True: #is_windows():
            date_label = wx.StaticText(self.panel, label="Date Range")
            date_label.SetFont(font)
            form_sizer.Add(date_label, 0, wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL)
            date_sizer = wx.BoxSizer(wx.HORIZONTAL)

            from_label = wx.StaticText(self.panel, label="from: ")
            from_label.SetFont(font)
            date_sizer.Add(from_label, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, font_size)

            self.start_time = wx.adv.TimePickerCtrl(self.panel)
            self.start_time.SetFont(font)
            date_sizer.Add(self.start_time, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, font_size)

            self.start_date = wx.adv.DatePickerCtrl(self.panel, style=wx.adv.DP_DROPDOWN)
            self.start_date.SetFont(font)
            date_sizer.Add(self.start_date, 0, wx.RIGHT, font_size)

            to_label = wx.StaticText(self.panel, label="to: ")
            to_label.SetFont(font)
            date_sizer.Add(to_label, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, font_size)

            self.end_time = wx.adv.TimePickerCtrl(self.panel)
            self.end_time.SetFont(font)
            date_sizer.Add(self.end_time, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, font_size)

            self.end_date = wx.adv.DatePickerCtrl(self.panel, style=wx.adv.DP_DROPDOWN)
            self.end_date.SetFont(font)
            date_sizer.Add(self.end_date, 0)
            form_sizer.Add(date_sizer, 1, wx.EXPAND)

        # Interval slider + text
        interval_label = wx.StaticText(self.panel, label="Interval (minutes)")
        interval_label.SetFont(font)
        form_sizer.Add(interval_label, 0, wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL)
        interval_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.interval_slider = wx.Slider(self.panel, value=INITIAL_SLIDER_VALUE, minValue=1, maxValue=60, style=wx.SL_HORIZONTAL)
        self.interval_slider.SetFont(font)
        interval_sizer.Add(self.interval_slider, 1, wx.RIGHT, 5)
        self.interval_txt = wx.TextCtrl(self.panel, value=f'{INITIAL_SLIDER_VALUE}', size=(50, -1))
        self.interval_txt.SetFont(font)
        interval_sizer.Add(self.interval_txt, 0)
        self.interval_slider.Bind(wx.EVT_SLIDER, self.on_slider_change)
        self.interval_txt.Bind(wx.EVT_TEXT, self.on_interval_txt_change)
        form_sizer.Add(interval_sizer, 1, wx.EXPAND)

        main_sizer.Add(form_sizer, 0, wx.ALL | wx.EXPAND, font_size)

        # Table for DataFrame display
        self.grid = wx.grid.Grid(self.panel)
        self.grid.CreateGrid(0, 0)
        self.grid.SetFont(font)
        main_sizer.Add(self.grid, 1, wx.ALL | wx.EXPAND, 5)

        # Buttons
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.start_btn = wx.Button(self.panel, label="Start Schedule")
        self.start_btn.SetFont(wx.Font(font_size + 4, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        self.start_btn.SetMinSize((140, 42))
        self.start_btn.Bind(wx.EVT_BUTTON, self.on_start_schedule)
        btn_sizer.Add(self.start_btn, 1, wx.ALL | wx.EXPAND, 10)

        self.cancel_btn = wx.Button(self.panel, label="Cancel Schedule")
        self.cancel_btn.SetFont(wx.Font(font_size + 4, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        self.cancel_btn.SetMinSize((140, 42))
        self.cancel_btn.Bind(wx.EVT_BUTTON, self.on_cancel_schedule)
        btn_sizer.Add(self.cancel_btn, 1, wx.ALL | wx.EXPAND, 10)
        main_sizer.Add(btn_sizer, 0, wx.EXPAND)

        outer_sizer = wx.BoxSizer(wx.VERTICAL)
        outer_sizer.Add(main_sizer, 1, wx.ALL | wx.EXPAND, border=10)
        self.panel.SetSizer(outer_sizer)
        self.Layout()

    def load_env(self):
        env = EnvManager()
        self.api_txt.SetValue(env.get(Env.API_KEY))
        self.prefix_txt.SetValue(env.get(Env.PREFIX))
        self.data_txt.SetValue(env.get(Env.DATA_FILEPATH))
        
        ts_from_str = env.get(Env.TIMESTAMP_FROM)
        ts_from = get_datetime_from_str(ts_from_str)
        self.start_date.SetValue(ts_from)
        self.start_time.SetValue(ts_from)

        ts_to_str = env.get(Env.TIMESTAMP_TO)
        ts_from = get_datetime_from_str(ts_to_str)
        self.end_date.SetValue(ts_from)
        self.end_time.SetValue(ts_from)
        
        self.interval_txt.SetValue(env.get(Env.INTERVAL))

    def store_env(self):
        env = EnvManager()
        env.set(Env.API_KEY, self.api_txt.GetValue())
        env.set(Env.PREFIX, self.prefix_txt.GetValue())
        env.set(Env.DATA_FILEPATH, self.data_txt.GetValue())

        date_from = self.start_date.GetValue()
        time_from = self.start_time.GetValue()
        ts_from_str = get_timestamp_str_from_date_time(date_from, time_from)

        date_to = self.end_date.GetValue()
        time_to = self.end_time.GetValue()
        ts_to_str = get_timestamp_str_from_date_time(date_to, time_to)

        env.set(Env.TIMESTAMP_FROM, ts_from_str)
        env.set(Env.TIMESTAMP_TO, ts_to_str)
        env.set(Env.INTERVAL, self.interval_txt.GetValue())

    def on_open(self, event):
        if event.IsShown():
            self.load_env()
        event.Skip()

    def on_close(self, event):
        self.store_env()
        self.Destroy()

    def on_browse(self, event):
        dlg = wx.FileDialog(self, message="Choose a CSV file",
                            defaultDir=self.last_dir,
                            wildcard="CSV files (*.csv)|*.csv",
                            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            self.data_txt.SetValue(path)
        dlg.Destroy()

    def on_data_txt_change(self, event):
        path = self.data_txt.GetValue()
        self.last_dir = os.path.dirname(path)
        try:
            df = read_file(path)
            self.reset_grid()
            self.display_dataframe(df)
        except Exception as e:
            self.reset_grid()

    def reset_grid(self):
        self.grid.ClearGrid()
        if self.grid.GetNumberRows() > 0:
            self.grid.DeleteRows(0, self.grid.GetNumberRows())
        if self.grid.GetNumberCols() > 0:
            self.grid.DeleteCols(0, self.grid.GetNumberCols())

        self.display_dataframe(pd.DataFrame())
        self.grid.ForceRefresh()

    def display_dataframe(self, df):
        self.grid.AppendCols(len(df.columns))
        self.grid.AppendRows(len(df))
        for col_idx, col_name in enumerate(df.columns):
            self.grid.SetColLabelValue(col_idx, col_name)
            for row_idx, value in enumerate(df[col_name]):
                self.grid.SetCellValue(row_idx, col_idx, str(value))

        self.grid.AutoSizeColumns()

    def on_slider_change(self, event):
        val = str(self.interval_slider.GetValue())
        self.interval_txt.ChangeValue(val)

    def on_interval_txt_change(self, event):
        val = self.interval_txt.GetValue()
        if val.isdigit():
            val_int = int(val)
            if 1 <= val_int <= 60:
                self.interval_slider.SetValue(val_int)

    def on_start_schedule(self, event):
        try:
            self.store_env()

            prefix = self.prefix_txt.GetValue()
            data_filepath = self.data_txt.GetValue()
            start_time = self.start_time.GetValue()
            start_date = self.start_date.GetValue()
            end_time = self.end_time.GetValue()
            end_date = self.end_date.GetValue()
            interval = self.interval_slider.GetValue()

            start_dt = datetime(start_date.year, start_date.month, start_date.day,
                                start_time.hour, start_time.minute)

            end_dt = datetime(end_date.year, end_date.month, end_date.day,
                              end_time.hour, end_time.minute)
            
            if end_dt <= start_dt:
                wx.MessageBox("Start datetime should be erlier than End datetime", "Error", wx.ICON_ERROR)
                return
            
            if not os.path.isfile(data_filepath):
                wx.MessageBox("Data filepath is not correct!", "Error", wx.ICON_ERROR)

            exe_filepath = get_current_exe_filepath()
            if not os.path.isfile(exe_filepath):
                wx.MessageBox("Internal error!", "Error", wx.ICON_ERROR)

            schedule_script(
                exe_filepath,
                ['--env'],
                start_dt,
                end_dt,
                interval
            )
            wx.MessageBox("Schedule done!", "Info")
        except:
            wx.MessageBox("Error while inserting schedule!", "Error", wx.ICON_ERROR)

    def on_cancel_schedule(self, event):
        try:
            remove_schedule()
            wx.MessageBox("Schedule removed!", "Info", wx.ICON_INFORMATION)
        except:
            wx.MessageBox("Error while removing schedule!", "Error", wx.ICON_ERROR)

def parse_args():
    """
    Parse command-line arguments.
    """
    parser = argparse.ArgumentParser(description="")
    parser.add_argument('--env', required=False,  help="Execute the actual data collection", action='store_true')
    return parser.parse_args()

def execute_collect_data():
    now = datetime.now()
    setup_logging('collect', now)

    env = EnvManager()
    prefix = str(env.get(Env.PREFIX))
    input_filepath = str(env.get(Env.DATA_FILEPATH))

    output_dirpath = get_api_output_dirpath(prefix)
    if not os.path.isdir(output_dirpath):
        os.mkdir(output_dirpath)

    collect_data(input_filepath, output_dirpath, prefix, now)

if __name__ == "__main__":
    args = parse_args()

    if args.env:
        execute_collect_data()
    else:
        app = wx.App(False)
        frame = SchedulerFrame()
        frame.Show()
        app.MainLoop()
