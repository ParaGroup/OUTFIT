"""
Author: Alberto Ottimo
Project: OUTFIT
Date: 2025-08-06
"""

import os
import argparse
import pandas as pd
from config import *
from utils import replace_extension
from utils import read_parquet_file
from utils import write_parquet_file, write_csv_file
from utils import split_file, merge_file

def read_csv_file(filename):
    engine = 'pyarrow' if USE_PYARROW else 'c'
    dtypes = {
        'X/m' : str,
        'Y/m' : str,
        'Z/m' : str
    }
    return pd.read_csv(filename, engine=engine, dtype=dtypes)

def read_file(filename, base_dir=None):
    filepath = os.path.join(base_dir, filename) if base_dir else filename

    if filename.endswith('.csv'):
        return read_csv_file(filepath)
    elif filename.endswith('.parquet'):
        return read_parquet_file(filepath)
    raise ValueError("Unknown file format")

def parse_args():
    """
    Parse command-line arguments.
    """
    parser = argparse.ArgumentParser(description='Convert data to csv/parquet formats')
    parser.add_argument('-i', '--input',                        help='Input filename')
    parser.add_argument('-c', '--csv',     action='store_true', help='Convert to csv')
    parser.add_argument('-p', '--parquet', action='store_true', help='Convert to parquet')
    parser.add_argument('-s', '--split',   action='store_true', help='Split parquet into parts')
    parser.add_argument('-m', '--merge',   action='store_true', help='Merge parts into parquet')
    return parser.parse_args()

def convert_to_parquet(input):
    output = replace_extension(input, '.parquet')
    df = read_file(input)
    write_parquet_file(df, output)
    print(f"File {input} converted to {output}")

def convert_to_csv(input):
    output = replace_extension(input, '.csv')
    df = read_file(input)
    write_csv_file(df, output)
    print(f"File {input} converted to {output}")

def split_parquet(input):
    split_file(input)

def merge_parquet(input):
    merge_file(input)


if __name__ == '__main__':
    args = parse_args()
    if args.parquet:
        convert_to_parquet(args.input)
    elif args.csv:
        convert_to_csv(args.input)
    elif args.split:
        split_parquet(args.input)
    elif args.merge:
        merge_parquet(args.input)
    else:
        print('Please specify the format!')