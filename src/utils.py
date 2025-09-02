"""
Authors: Pasquale Gorrasi & Alberto Ottimo
Project: OUTFIT
Date: 2025-07-25
"""

from config import *
import platform
import subprocess
import sys
import os
import io
import csv
import logging
import time
import glob
from pathlib import Path
from enum import Enum
from dotenv import load_dotenv, set_key, unset_key
from datetime import datetime, timedelta
import pandas as pd
import shutil
import locale


#------------------------------------------------------------------------------
#
# Logging functions
#
#------------------------------------------------------------------------------

def generate_filename_timestamp(now: datetime) -> str:
    return now.strftime("%Y%m%d-%H%M-%A")

def generate_log_filename(name: str, now: datetime) -> str:
    """
    Generate a log filename with format:
    "logs/{name}-{year}-{month}-{day}-{hour}-{minute}-{weekday}.log".
    Example: "logs/collect-2025-07-28-14-30-Monday.csv"
    """
    dir = os.path.abspath("logs")
    timestamp = generate_filename_timestamp(now)
    filename = f"{name}-{timestamp}.log"
    return os.path.join(dir, filename)

def generate_output_filename(dir:str, prefix: str, now: datetime) -> str:
    """
    Generate an output filename with format:
    "{dir}/{prefix}-{year}-{month}-{day}-{hour}-{minute}-{weekday}.csv"
    Example: "data/pisa-2025-07-28-14-30-Monday.csv"
    """
    timestamp = generate_filename_timestamp(now)
    filename = f"{prefix}-{timestamp}.csv"
    return os.path.join(dir, filename)

def get_api_output_dirpath(data_dirname: str = "", prefix: str = ""):
    return os.path.join(data_dirname, prefix, API_OUTPUT_DIRNAME)


#------------------------------------------------------------------------------
#
# Logging functions
#
#------------------------------------------------------------------------------

def setup_logging(name: str, now: datetime, debug=False, to_file = True):
    log_path = generate_log_filename(name, now)
    os.makedirs(os.path.dirname(log_path), exist_ok=True)

    handlers = [logging.StreamHandler()]
    if to_file:
        handlers.append(logging.FileHandler(log_path))

    logging.basicConfig(
        level=(logging.DEBUG if debug else logging.INFO),
        format="%(asctime)-15s - %(levelname)-8s - %(message)s",
        handlers=handlers
    )


#------------------------------------------------------------------------------
#
# Decorators
#
#------------------------------------------------------------------------------

def debug_info(print_info=PRINT_INFO, dump=DUMP_RESULTS):
    def decorator(func):
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            if print_info:
                logging.debug(f"{func.__name__}:")
                logging.debug(result.info())
                logging.debug(result.head())
            if dump:
                result.to_csv(f'{func.__name__}.csv', index=None)
            return result
        return wrapper
    return decorator

def timer(func):
    def wrapper(*args, **kwargs):
        global total_time
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        elapsed_time_ms = (end_time - start_time) * 1000
        logging.debug(f"{elapsed_time_ms:10.3f} ms : {func.__name__}")
        return result
    return wrapper


#------------------------------------------------------------------------------
#
# File I/O functions
#
#------------------------------------------------------------------------------

def remove_extension(filename):
    filename, _ = os.path.splitext(filename)
    return filename

def replace_extension(filename, new_ext):
    _, ext = os.path.splitext(filename)
    return filename.replace(ext, new_ext)

def split_file(input_filename, part_size = 42):
    """
    Splits the file at 'input_filename' into parts of size 'part_size' bytes.
    Each part will be named as {filename}.part{n:03d}
    """
    part_size_mb = part_size * 1024 * 1024
    # filename = os.path.basename(input_filename)
    filename = remove_extension(input_filename)
    with open(input_filename, 'rb') as f:
        part_num = 0
        while True:
            chunk = f.read(part_size_mb)
            if not chunk:
                break
            part_filename = f"{filename}.part{part_num:03d}"
            with open(part_filename, 'wb') as pf:
                pf.write(chunk)
            part_num += 1
    print(f"File '{filename}' split into {part_num} parts.")

def get_part_filenames(filename):
    base_filename = remove_extension(filename)
    part_pattern = f"{base_filename}.part*"
    return sorted(glob.glob(part_pattern))

def merge_file(output_filename):
    """
    Merges parts named {output_filename}.part{n:03d} from 'directory'
    into a single file with the name 'output_filename'.
    """
    parts = get_part_filenames(output_filename)

    if not parts:
        raise FileNotFoundError("No parts found to merge.")

    with open(output_filename, 'wb') as outfile:
        for part in parts:
            with open(part, 'rb') as pf:
                outfile.write(pf.read())
    print(f"Merged {len(parts)} parts into '{output_filename}'.")

@timer
def read_json_file(filename):
    return pd.read_json(filename)

@timer
def read_csv_file(filename):
    if USE_PYARROW:
        return pd.read_csv(filename, engine="pyarrow")
    return pd.read_csv(filename)

@timer
def read_parquet_file(filename):
    if USE_PYARROW:
        return pd.read_parquet(filename, engine="pyarrow")
    return pd.read_parquet(filename)

def read_file(filename, base_dir=None):
    filepath = os.path.join(base_dir, filename) if base_dir else filename

    if filename.endswith('.json'):
        return read_json_file(filepath)
    elif filename.endswith('.csv'):
        return read_csv_file(filepath)
    elif filename.endswith('.parquet'):
        return read_parquet_file(filepath)
    raise ValueError("Unknown file format")

@timer
def write_csv_file(df, filename):
    df.to_csv(filename, index=False, quoting=csv.QUOTE_STRINGS, decimal=".")

@timer
def write_json_file(df, filename):
    df.to_json(filename, index=False)

@timer
def write_parquet_file(df, filename):
    df.to_parquet(filename, index=False)


#------------------------------------------------------------------------------
#
# .env Manager
#
#------------------------------------------------------------------------------

class Env(Enum):
    API_KEY = "API_KEY"
    PREFIX = "PREFIX"
    STREETS_FILEPATH = "STREETS_FILEPATH"
    TIMESTAMP_FROM = "TIMESTAMP_FROM"
    TIMESTAMP_TO = "TIMESTAMP_TO"
    INTERVAL = "INTERVAL"
    PROCESS_DATA = "PROCESS_DATA"
    ATTENUATION_MATRIX = "ATTENUATION_MATRIX"
    STREET_PARAMS = "STREET_PARAMS"
    FREQ_COEFFS = "FREQ_COEFFS"
    CURVE_A = "CURVE_A"

class EnvManager:
    def __init__(self, filepath=".env"):
        self.filepath = filepath
        if not os.path.exists(self.filepath):
            with open(self.filepath, "w"):
                pass
        load_dotenv(dotenv_path=self.filepath, override=True)

    def get(self, field: Env, default=None):
        return os.getenv(field.value, default)

    def get_bool(self, field: Env, default=False):
        return os.getenv(field.value, str(default)).lower() == "true"

    def set(self, field: Env, value: str):
        set_key(str(self.filepath), field.value, value)

    def set_bool(self, field: Env, value: bool):
        set_key(str(self.filepath), field.value, str(value))

    def delete(self, field: Env):
        unset_key(str(self.filepath), field.value)


#------------------------------------------------------------------------------
#
# Schedule script
#
#------------------------------------------------------------------------------

def is_unix() -> bool:
    return platform.system() in ["Linux", "Darwin"]

def is_windows() -> bool:
    return platform.system() == "Windows"

def date_windows_locale_str(dt: datetime) -> str:
    if locale.getlocale(locale.LC_TIME) == (None, None):
        locale.setlocale(locale.LC_TIME, "")
    return dt.strftime("%x")

def time_windows_locale_str(dt: datetime) -> str:
    if locale.getlocale(locale.LC_TIME) == (None, None):
        locale.setlocale(locale.LC_TIME, "")
    return dt.strftime("%X")

def schedule_on_unix(script_path, args, interval_minutes, prefix=SCHEDULE_PREFIX):
    job_name = f"{prefix}_{datetime.now().strftime('%Y%m%d-%H%M')}"
    cron_expr = f"*/{interval_minutes} * * * *"
    cron_command = f"{cron_expr} {sys.executable} {script_path} {' '.join(args)} # {job_name}"

    result = subprocess.run("crontab -l", shell=True, capture_output=True, text=True)
    existing_crontab = result.stdout if result.returncode == 0 else ""

    new_crontab = existing_crontab + "\n" + cron_command + "\n"
    subprocess.run(f"(echo '{new_crontab}') | crontab -", shell=True)
    print(f"Cron job scheduled every {interval_minutes} minutes on Unix.")

def schedule_on_windows(script_path, args, start_dt, end_dt, interval_minutes, prefix=SCHEDULE_PREFIX):
    if shutil.which("schtasks") is None:
        raise RuntimeError("Windows Task Scheduler (schtasks) not found.")

    if interval_minutes < 1 or interval_minutes > 1439:
        raise ValueError("Interval must be between 1 and 1439 minutes on Windows.")

    # Workaround on schtasks.exe to satisfy:
    # (end_time - start_time) > interval
    # only when end_time > start_time
    start_time = datetime(start_dt.year, start_dt.month, start_dt.day, start_dt.hour, start_dt.minute)
    end_time = datetime(start_dt.year, start_dt.month, start_dt.day, end_dt.hour, end_dt.minute)

    if end_time >= start_time:
        diff = end_time - start_time
        if diff <= timedelta(minutes=interval_minutes):
            compensation = (timedelta(minutes=interval_minutes + 1) - diff)
            end_time = end_time + compensation

    task_name = f"{prefix}_{datetime.now().strftime('%Y%m%d-%H%M')}"
    start_date_str = date_windows_locale_str(start_dt)
    start_time_str = time_windows_locale_str(start_time)
    end_date_str = date_windows_locale_str(end_dt)
    end_time_str = time_windows_locale_str(end_time)

    quoted_args = ' '.join(args)
    full_cmd = f'{script_path} {quoted_args}'

    # Build schtasks command
    create_cmd = [
        "schtasks",
        "/Create",
        "/TN", task_name,
        "/TR", full_cmd,
        "/SC", "MINUTE",
        "/MO", str(interval_minutes),
        "/ST", start_time_str,
        "/SD", start_date_str,
        "/ED", end_date_str,
        "/ET", end_time_str,
        "/F",
        "/RL", "LIMITED"
    ]

    try:
        subprocess.run(create_cmd, check=True)
        print(f"Windows task '{task_name}' scheduled successfully.")
    except subprocess.CalledProcessError as e:
        print("Failed to schedule task:", e)
        raise Exception("Failed to schedule task")

def remove_cron_jobs_with_prefix(prefix=SCHEDULE_PREFIX):
    result = subprocess.run("crontab -l", shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print("No crontab found.")
        return

    lines = result.stdout.strip().splitlines()
    filtered_lines = [line for line in lines if f"# {prefix}" not in line]

    updated_crontab = "\n".join(filtered_lines)
    subprocess.run(f"(echo '{updated_crontab}') | crontab -", shell=True)
    print(f"Removed cron jobs with prefix '{prefix}'")

def remove_windows_tasks_with_prefix(prefix = SCHEDULE_PREFIX):
    if shutil.which("schtasks") is None:
        raise RuntimeError("Windows Task Scheduler (schtasks) not found.")
    try:
        result = subprocess.run(
            ["schtasks", "/Query", "/FO", "CSV"],
            capture_output=True, text=True, check=True
        )

        csv_reader = csv.reader(io.StringIO(result.stdout))
        rows = list(csv_reader)
        if not rows:
            print("No task found!")
            return

        task_names = [row[0] for row in rows[1:] if row and row[0].startswith(f"\\{prefix}")]

        for task_name in task_names:
            try:
                subprocess.run(
                    ["schtasks", "/Delete", "/TN", task_name, "/F"],
                    check=True
                )
                print(f"Deleted task: {task_name}")
            except subprocess.CalledProcessError as e:
                print(f"Failed to delete task {task_name}: {e}")
    except subprocess.CalledProcessError as e:
        print("Failed to query scheduled tasks:", e)

def schedule_script(script_path, script_args, start_dt, end_dt, interval_minutes, prefix=SCHEDULE_PREFIX):
    if is_unix():
        # schedule_on_unix(script_path, script_args, interval_minutes, prefix)
        raise NotImplementedError("Linux and Darwin are not supported yet!")
    elif is_windows():
        schedule_on_windows(script_path, script_args, start_dt, end_dt, interval_minutes, prefix)
    else:
        raise NotImplementedError("Unsupported OS")

def remove_schedule(prefix=SCHEDULE_PREFIX):
    if is_unix():
        # remove_cron_jobs_with_prefix(prefix)
        raise NotImplementedError("Linux and Darwin are not supported yet!")
    elif is_windows():
        remove_windows_tasks_with_prefix(prefix)
    else:
        raise NotImplementedError("Unsupported OS")