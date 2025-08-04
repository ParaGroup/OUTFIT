from config import *
import platform
import subprocess
import sys
import os
import csv
import logging
import time
from datetime import datetime
import pandas as pd


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
    dir = "logs"
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


#------------------------------------------------------------------------------
#
# Logging functions
#
#------------------------------------------------------------------------------

def setup_logging(name: str, now: datetime, debug=False):
    log_path = generate_log_filename(name, now)
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    logging.basicConfig(
        level=(logging.DEBUG if debug else logging.INFO),
        format="%(asctime)-15s - %(levelname)-8s - %(message)s",
        handlers=[
            logging.FileHandler(log_path),
            logging.StreamHandler()
        ]
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

def replace_extension(filename, new_ext):
    _, ext = os.path.splitext(filename)
    return filename.replace(ext, new_ext)

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
    df.to_csv(filename, index=False, quoting=csv.QUOTE_STRINGS)

@timer
def write_json_file(df, filename):
    df.to_json(filename, index=False)

@timer
def write_parquet_file(df, filename):
    df.to_parquet(filename, index=False)


#------------------------------------------------------------------------------
#
# Schedule script
#
#------------------------------------------------------------------------------

# def schedule_on_unix(script_path, args, interval_minutes, prefix=SCHEDULE_PREFIX):
#     job_name = f"{prefix}{int(datetime.now().timestamp())}"
#     cron_expr = f"*/{interval_minutes} * * * *"
#     cron_command = f"{cron_expr} {sys.executable} {script_path} {' '.join(args)} # {job_name}"

#     result = subprocess.run("crontab -l", shell=True, capture_output=True, text=True)
#     existing_crontab = result.stdout if result.returncode == 0 else ""

#     new_crontab = existing_crontab + "\n" + cron_command + "\n"
#     subprocess.run(f"(echo '{new_crontab}') | crontab -", shell=True)
#     print(f"Cron job scheduled every {interval_minutes} minutes on Unix.")

def schedule_on_windows(script_path, args, start_dt, end_dt, interval_minutes, prefix=SCHEDULE_PREFIX):
    import shutil
    if shutil.which("schtasks") is None:
        raise RuntimeError("Windows Task Scheduler (schtasks) not found.")

    if interval_minutes < 1 or interval_minutes > 1439:
        raise ValueError("Interval must be between 1 and 1439 minutes on Windows.")

    task_name = f"{prefix}{int(datetime.now().timestamp())}"
    start_time = start_dt.strftime("%H:%M")
    start_date = start_dt.strftime("%m/%d/%Y")
    end_date = end_dt.strftime("%m/%d/%Y")

    argument_str = ' '.join(args)
    full_cmd = f'"{sys.executable}" "{script_path}" {argument_str}'

    create_cmd = (
        f'schtasks /Create /TN "{task_name}" /TR {full_cmd} /SC MINUTE /MO {interval_minutes} '
        f'/ST {start_time} /SD {start_date} /ED {end_date} /F'
    )

    subprocess.run(create_cmd, shell=True, check=True)
    print(f"Windows task scheduled every {interval_minutes} minutes.")

def schedule_script(script_path, script_args, start_dt, end_dt, interval_minutes, prefix=SCHEDULE_PREFIX):
    if platform.system() in ["Linux", "Darwin"]:
        # schedule_on_unix(script_path, script_args, interval_minutes, prefix)
        raise NotImplementedError("Linux and Darwin are not supported yet!")
    elif platform.system() == "Windows":
        schedule_on_windows(script_path, script_args, start_dt, end_dt, interval_minutes, prefix)
    else:
        raise NotImplementedError("Unsupported OS")
    
# def remove_cron_jobs_with_prefix(prefix=SCHEDULE_PREFIX):
#     result = subprocess.run("crontab -l", shell=True, capture_output=True, text=True)
#     if result.returncode != 0:
#         print("No crontab found.")
#         return

#     lines = result.stdout.strip().splitlines()
#     filtered_lines = [line for line in lines if f"# {prefix}" not in line]

#     updated_crontab = "\n".join(filtered_lines)
#     subprocess.run(f"(echo '{updated_crontab}') | crontab -", shell=True)
#     print(f"Removed cron jobs with prefix '{prefix}'")

def remove_windows_tasks_with_prefix(prefix=SCHEDULE_PREFIX):
    result = subprocess.run('schtasks /Query /FO LIST /V', capture_output=True, text=True, shell=True)
    if result.returncode != 0:
        print("Failed to query scheduled tasks.")
        return

    tasks_output = result.stdout
    tasks = [line for line in tasks_output.splitlines() if line.startswith("TaskName:")]

    for task in tasks:
        task_name = task.split(":", 1)[1].strip()
        if f"\\{prefix}" in task_name:
            print(f"Deleting task: {task_name}")
            subprocess.run(f'schtasks /Delete /TN "{task_name}" /F', shell=True)

    print(f"Removed scheduled tasks with prefix '{prefix}'")

def remove_schedule(prefix=SCHEDULE_PREFIX):
    if platform.system() in ["Linux", "Darwin"]:
        # remove_cron_jobs_with_prefix(prefix)
        raise NotImplementedError("Linux and Darwin are not supported yet!")
    elif platform.system() == "Windows":
        remove_windows_tasks_with_prefix(prefix)
    else:
        raise NotImplementedError("Unsupported OS")