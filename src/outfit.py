"""
Author: Alberto Ottimo
Project: OUTFIT
Date: 2025-08-06
"""

import wx
import wx.adv
import wx.grid
import os
import argparse
import pandas as pd
from datetime import datetime, timedelta
from utils import *
from collect_data import collect_data
from process import process_data


INITIAL_SLIDER_VALUE = 10
FONT_SIZE = 16
SPACER = 16
LARGE_SPACER = 32


def get_datetime_from_str(timestamp_str):
    if timestamp_str:
        return datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
    return datetime.now()

def get_timestamp_str_from_date_time(date, time):
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


class SchedulerFrame(wx.Frame):
    def __init__(self):
        super().__init__(None, title="OUTFIT", size=(1024, 768))
        self.Bind(wx.EVT_CLOSE, self.on_close)
        self.Bind(wx.EVT_SHOW, self.on_open)

        self.panel = wx.Panel(self)
        self.last_dir = os.getcwd()

        font = wx.Font(FONT_SIZE, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        form_sizer = wx.FlexGridSizer(rows=0, cols=2, hgap=FONT_SIZE, vgap=FONT_SIZE)
        form_sizer.AddGrowableCol(1, 1)

        # API Key
        api_label = wx.StaticText(self.panel, label="API KEY")
        api_label.SetFont(font)

        self.api_txt = wx.TextCtrl(self.panel, style=wx.TE_PROCESS_ENTER)
        self.api_txt.SetFont(font)

        form_sizer.Add(api_label, 0, wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL)
        form_sizer.Add(self.api_txt, 1, wx.EXPAND)


        # Prefix
        prefix_label = wx.StaticText(self.panel, label="Prefix")
        prefix_label.SetFont(font)

        self.prefix_txt = wx.TextCtrl(self.panel)
        self.prefix_txt.SetFont(font)

        form_sizer.Add(prefix_label, 0, wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL)
        form_sizer.Add(self.prefix_txt, 1, wx.EXPAND)


        # Data File Input with Browse
        data_label = wx.StaticText(self.panel, label="Data")
        data_label.SetFont(font)

        self.data_txt = wx.TextCtrl(self.panel)
        self.data_txt.SetFont(font)
        self.data_txt.Bind(wx.EVT_TEXT, self.on_data_txt_change)

        browse_btn = wx.Button(self.panel, label="Browse")
        browse_btn.SetFont(font)
        browse_btn.Bind(wx.EVT_BUTTON, self.on_browse)

        data_input_sizer = wx.BoxSizer(wx.HORIZONTAL)
        data_input_sizer.Add(self.data_txt, 1, wx.RIGHT, 5)
        data_input_sizer.Add(browse_btn, 0)

        form_sizer.Add(data_label, 0, wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL)
        form_sizer.Add(data_input_sizer, 1, wx.EXPAND | wx.ALIGN_CENTER_VERTICAL)


        # Start & End Date
        if True: # is_windows():
            date_label = wx.StaticText(self.panel, label="Date Range")
            date_label.SetFont(font)

            from_label = wx.StaticText(self.panel, label="from: ")
            from_label.SetFont(font)

            self.start_time = wx.adv.TimePickerCtrl(self.panel)
            self.start_time.SetFont(font)

            self.start_date = wx.adv.DatePickerCtrl(self.panel, style=wx.adv.DP_DROPDOWN)
            self.start_date.SetFont(font)

            to_label = wx.StaticText(self.panel, label="to: ")
            to_label.SetFont(font)

            self.end_time = wx.adv.TimePickerCtrl(self.panel)
            self.end_time.SetFont(font)

            self.end_date = wx.adv.DatePickerCtrl(self.panel, style=wx.adv.DP_DROPDOWN)
            self.end_date.SetFont(font)

            date_sizer = wx.BoxSizer(wx.HORIZONTAL)
            date_sizer.Add(from_label, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, SPACER)
            date_sizer.Add(self.start_time, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, SPACER)
            date_sizer.Add(self.start_date, 0, wx.RIGHT, LARGE_SPACER)
            date_sizer.Add(to_label, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, SPACER)
            date_sizer.Add(self.end_time, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, SPACER)
            date_sizer.Add(self.end_date, 0)

            form_sizer.Add(date_label, 0, wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL)
            form_sizer.Add(date_sizer, 1, wx.EXPAND)


        # Interval slider + text
        interval_label = wx.StaticText(self.panel, label="Interval (minutes)")
        interval_label.SetFont(font)

        self.interval_txt = wx.TextCtrl(self.panel, value=f'{INITIAL_SLIDER_VALUE}', size=(50, -1))
        self.interval_txt.SetFont(font)
        self.interval_txt.Bind(wx.EVT_TEXT, self.on_interval_txt_change)

        self.interval_slider = wx.Slider(self.panel, value=INITIAL_SLIDER_VALUE, minValue=1, maxValue=60, style=wx.SL_HORIZONTAL | wx.SL_MIN_MAX_LABELS)
        self.interval_slider.SetFont(font)
        self.interval_slider.Bind(wx.EVT_SLIDER, self.on_slider_change)

        # Process Data Checkbox
        # self.process_data_checkbox = wx.CheckBox(self.panel, label="Process Collected Data")
        # self.process_data_checkbox.SetFont(font)

        interval_sizer = wx.BoxSizer(wx.HORIZONTAL)
        interval_sizer.Add(self.interval_txt, 0, wx.ALIGN_CENTER_VERTICAL, SPACER)
        interval_sizer.AddSpacer(SPACER)
        interval_sizer.Add(self.interval_slider, 1, wx.RIGHT, SPACER)
        # interval_sizer.AddSpacer(SPACER)
        # interval_sizer.Add(self.process_data_checkbox, 0, wx.ALIGN_CENTER_VERTICAL, SPACER)

        # interval_sizer.Add(self.process_data_checkbox, 0, wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL)
        form_sizer.Add(interval_label, 0, wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL)
        form_sizer.Add(interval_sizer, 1, wx.EXPAND)
        main_sizer.Add(form_sizer, 0, wx.ALL | wx.EXPAND, SPACER)


        # Table for DataFrame display
        self.grid = wx.grid.Grid(self.panel)
        self.grid.CreateGrid(0, 0)
        self.grid.SetFont(font)
        main_sizer.Add(self.grid, 1, wx.ALL | wx.EXPAND, 5)


        # Buttons
        self.start_schedule_btn = wx.Button(self.panel, label="Start Schedule")
        self.start_schedule_btn.SetFont(wx.Font(FONT_SIZE + 4, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        self.start_schedule_btn.SetMinSize((140, 42))
        self.start_schedule_btn.Bind(wx.EVT_BUTTON, self.on_start_schedule)

        self.remove_schedules_btn = wx.Button(self.panel, label="Remove Schedules")
        self.remove_schedules_btn.SetFont(wx.Font(FONT_SIZE + 4, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        self.remove_schedules_btn.SetMinSize((140, 42))
        self.remove_schedules_btn.Bind(wx.EVT_BUTTON, self.on_cancel_schedule)

        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        btn_sizer.Add(self.start_schedule_btn, 1, wx.ALL | wx.EXPAND, SPACER)
        btn_sizer.Add(self.remove_schedules_btn, 1, wx.ALL | wx.EXPAND, SPACER)
        main_sizer.Add(btn_sizer, 0, wx.EXPAND)

        outer_sizer = wx.BoxSizer(wx.VERTICAL)
        outer_sizer.Add(main_sizer, 1, wx.ALL | wx.EXPAND, border=10)
        self.panel.SetSizer(outer_sizer)
        self.Layout()


    def load_env(self):
        try:
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
            # self.process_data_checkbox.SetValue(env.get(Env.PROCESS_DATA))

            logging.info("Environment variables loaded successfully.")
        except Exception as e:
            logging.error(f"Failed to load environment variables: {e}")

    def store_env(self, filename: str = ".env"):
        try:
            env = EnvManager(filename)
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
            # env.set(Env.PROCESS_DATA, self.process_data_checkbox.GetValue())

            logging.info(f"Environment variables stored to {filename}")
        except Exception as e:
            logging.error(f"Failed to store environment variables: {e}")

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
            logging.info(f"Loaded data file: {path}")
            self.reset_grid()
            self.display_dataframe(df)
        except Exception as e:
            logging.error(f"Failed to load data file {path}: {e}")
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
            prefix = self.prefix_txt.GetValue()
            data_filepath = self.data_txt.GetValue()
            start_time = wxDateTime_to_datetime(self.start_time.GetValue())
            start_date = wxDateTime_to_datetime(self.start_date.GetValue())
            end_time = wxDateTime_to_datetime(self.end_time.GetValue())
            end_date = wxDateTime_to_datetime(self.end_date.GetValue())
            interval = self.interval_slider.GetValue()

            start_dt = datetime(start_date.year, start_date.month, start_date.day,
                                start_time.hour, start_time.minute)
            end_dt = datetime(end_date.year, end_date.month, end_date.day,
                            end_time.hour, end_time.minute)

            env_filepath = f'{prefix}_{start_dt.strftime("%Y%m%d-%H%M")}.env'

            self.store_env()
            self.store_env(env_filepath)

            env_abs_filepath = os.path.abspath(env_filepath)

            if start_dt < datetime.now():
                logging.warning("Start datetime is in the past.")
                wx.MessageBox("Start date and time should be after the current date and time!", "Error", wx.ICON_ERROR)
                return

            if end_dt <= start_dt:
                logging.warning("Start datetime is not earlier than end datetime.")
                wx.MessageBox("Start datetime should be earlier than end datetime!", "Error", wx.ICON_ERROR)
                return

            if not os.path.isfile(data_filepath):
                logging.error(f"Data filepath does not exist: {data_filepath}")
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

def parse_args():
    """
    Parse command-line arguments.
    """
    parser = argparse.ArgumentParser(description="")
    parser.add_argument('--env', required=False,  help="Execute the actual data collection.")
    # parser.add_argument('--process', required=False, help="After data collection, starts the data process.", action="store_true")
    return parser.parse_args()

def execute_collect_data(env_filepath: str = ".env"):
    try:
        now = datetime.now()
        env = EnvManager(env_filepath)
        api_key = str(env.get(Env.API_KEY))
        prefix = str(env.get(Env.PREFIX))
        input_filepath = str(env.get(Env.DATA_FILEPATH))

        data_dirname = os.path.dirname(input_filepath)
        output_dirpath = get_api_output_dirpath(data_dirname)
        if not os.path.isdir(output_dirpath):
            os.mkdir(output_dirpath)
            logging.info(f"Created output directory: {output_dirpath}")

        logging.info(f"Collecting data with prefix={prefix}, input={input_filepath}, output={output_dirpath}")
        collect_data(api_key, input_filepath, output_dirpath, prefix, now)

        return now
    except Exception as e:
        logging.error(f"Data collection failed: {e}")
        raise

# def execute_process_data(now: datetime, env_filepath: str = ".env"):
#     try:
#         env = EnvManager(env_filepath)
#         prefix = str(env.get(Env.PREFIX))
#         input_filepath = str(env.get(Env.DATA_FILEPATH))
#         data_dirname = os.path.dirname(input_filepath)
#         output_dirpath = get_api_output_dirpath(data_dirname)
#         output_filename = generate_output_filename(output_dirpath, prefix, now)

#         process_data(output_filename, )
#         pass
#     except Exception as e:
#         logging.error(f"Data processing failed: {e}")
#         raise


if __name__ == "__main__":
    now = datetime.now()
    setup_logging('collect_gui', now, to_file=False)

    args = parse_args()

    if args.env:
        try:
            data_now = execute_collect_data(args.env)
            # if args.process:
            #     execute_process_data(data_now, args.env)
        except:
            pass

    else:
        app = wx.App(False)
        frame = SchedulerFrame()
        frame.Show()
        app.MainLoop()