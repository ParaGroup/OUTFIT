import wx
import wx.grid as gridlib
import wx.adv
import pandas as pd
import os
from datetime import datetime
from dotenv import load_dotenv, set_key
from utils import schedule_script, remove_schedule

API_KEY_FIELD = "GOOGLE_API_KEY"
PREFIX_FIELD = 'PREFIX'
ENV_FILE = ".env"
INITIAL_SLIDER_VALUE = 10

class SchedulerFrame(wx.Frame):
    def __init__(self):
        super().__init__(None, title="Scheduler GUI", size=(800, 600))
        self.panel = wx.Panel(self)
        self.last_dir = os.getcwd()

        self.load_env()

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
        self.api_txt.SetValue(self.api_key)
        self.api_txt.Bind(wx.EVT_KILL_FOCUS, self.save_api_key)
        form_sizer.Add(self.api_txt, 1, wx.EXPAND)

        # Prefix
        prefix_label = wx.StaticText(self.panel, label="Prefix")
        prefix_label.SetFont(font)
        form_sizer.Add(prefix_label, 0, wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL)
        self.prefix_txt = wx.TextCtrl(self.panel)
        self.prefix_txt.SetFont(font)
        self.prefix_txt.SetValue(self.prefix)
        self.prefix_txt.Bind(wx.EVT_KILL_FOCUS, self.save_prefix)
        form_sizer.Add(self.prefix_txt, 1, wx.EXPAND)

        # Data File Input with Browse
        data_label = wx.StaticText(self.panel, label="Data")
        data_label.SetFont(font)
        form_sizer.Add(data_label, 0, wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL)
        data_input_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.data_txt = wx.TextCtrl(self.panel)
        self.data_txt.SetFont(font)
        data_input_sizer.Add(self.data_txt, 1, wx.RIGHT, 5)
        browse_btn = wx.Button(self.panel, label="Browse")
        browse_btn.SetFont(font)
        browse_btn.Bind(wx.EVT_BUTTON, self.on_browse)
        data_input_sizer.Add(browse_btn, 0)
        form_sizer.Add(data_input_sizer, 1, wx.EXPAND)

        # Start & End Date
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
        self.interval_txt.Bind(wx.EVT_TEXT, self.on_text_change)
        form_sizer.Add(interval_sizer, 1, wx.EXPAND)

        main_sizer.Add(form_sizer, 0, wx.ALL | wx.EXPAND, font_size)

        # Table for DataFrame display
        self.grid = gridlib.Grid(self.panel)
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
        if os.path.exists(ENV_FILE):
            load_dotenv(ENV_FILE)
            self.api_key = os.getenv(API_KEY_FIELD, "")
            self.prefix = os.getenv(PREFIX_FIELD, "")
        else:
            self.api_key = ""
            self.prefix = ""

    def save_api_key(self, event=None):
        key = self.api_txt.GetValue()
        with open(ENV_FILE, "a+") as f:
            set_key(ENV_FILE, API_KEY_FIELD, key)
    
    def save_prefix(self, event=None):
        prefix = self.prefix_txt.GetValue()
        with open(ENV_FILE, "a+") as f:
            set_key(ENV_FILE, PREFIX_FIELD, prefix)

    def on_browse(self, event):
        dlg = wx.FileDialog(self, message="Choose a CSV file",
                            defaultDir=self.last_dir,
                            wildcard="CSV files (*.csv)|*.csv",
                            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            self.data_txt.SetValue(path)
            self.last_dir = os.path.dirname(path)
            self.load_csv(path)
        dlg.Destroy()

    def load_csv(self, path):
        try:
            df = pd.read_csv(path)
            self.display_dataframe(df)
        except Exception as e:
            wx.MessageBox(f"Failed to load CSV:\n{e}", "Error", wx.OK | wx.ICON_ERROR)

    def display_dataframe(self, df):
        self.grid.ClearGrid()
        if self.grid.GetNumberRows() > 0:
            self.grid.DeleteRows(0, self.grid.GetNumberRows())
        if self.grid.GetNumberCols() > 0:
            self.grid.DeleteCols(0, self.grid.GetNumberCols())

        self.grid.AppendCols(len(df.columns))
        self.grid.AppendRows(len(df))

        for col_idx, col_name in enumerate(df.columns):
            self.grid.SetColLabelValue(col_idx, col_name)
            for row_idx, value in enumerate(df[col_name]):
                self.grid.SetCellValue(row_idx, col_idx, str(value))

        self.grid.AutoSizeColumns()

    def on_slider_change(self, event):
        val = self.interval_slider.GetValue()
        self.interval_txt.ChangeValue(str(val))

    def on_text_change(self, event):
        val = self.interval_txt.GetValue()
        if val.isdigit():
            val_int = int(val)
            if 1 <= val_int <= 60:
                self.interval_slider.SetValue(val_int)

    def on_start_schedule(self, event):
        try:
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
            
            data_dirname = os.path.dirname(data_filepath)
            output_dirpath = os.path.join(data_dirname, "api_output")

            if not os.path.isfile(data_dirname):
                wx.MessageBox("Data is not a file or does not exists!", "Error", wx.ICON_ERROR)
                return

            if not os.path.isdir(output_dirpath):
                os.mkdir(output_dirpath)

            schedule_script(
                os.path.abspath("src/collect_data.py"),
                ["-i", data_filepath,
                 "-d", output_dirpath,
                 "-p", prefix],
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
        

if __name__ == "__main__":
    app = wx.App(False)
    frame = SchedulerFrame()
    frame.Show()
    app.MainLoop()
