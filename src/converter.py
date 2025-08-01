import argparse
import pandas as pd
from utils import *


def parse_args():
    """
    Parse command-line arguments.
    """
    parser = argparse.ArgumentParser(description='Convert data to csv, json or parquet formats')
    parser.add_argument('-i', '--input', type=str, help='Input filename')
    parser.add_argument('-c', '--csv', action='store_true', help='Convert to csv')
    parser.add_argument('-j', '--json', action='store_true', help='Convert to json')
    parser.add_argument('-p', '--parquet', action='store_true', help='Convert to parquet')
    return parser.parse_args()

def convert_to_parquet(input):
    output = replace_extension(input, '.parquet')
    df = read_file(input)
    write_parquet_file(df, output)
    print(f"File {input} converted to {output}")

def convert_to_json(input):
    output = replace_extension(input, '.json')
    df = read_file(input)
    write_json_file(df, output)
    print(f"File {input} converted to {output}")

def convert_to_csv(input):
    output = replace_extension(input, '.csv')
    df = read_file(input)
    df.to_csv(output, index=False)
    print(f"File {input} converted to {output}")


if __name__ == '__main__':
    args = parse_args()

    if args.parquet:
        convert_to_parquet(args.filename)
    elif args.json:
        convert_to_json(args.filename)
    elif args.csv:
        convert_to_csv(args.filename)
    else:
        print('Please specify the format!')