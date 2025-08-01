from config import *
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
