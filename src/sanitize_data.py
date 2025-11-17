"""
Authors: Pasquale Gorrasi & Alberto Ottimo
Project: OUTFIT
Date: 2025-07-25
"""

import os
import sys
import argparse
from datetime import datetime
import pandas as pd
from utils import *


def parse_args():
    """
    Parse command-line arguments.
    """
    parser = argparse.ArgumentParser(description="Collect data using Google Directions API.")
    parser.add_argument('-i', '--input',  required=True, help='Folder containing old data format files.')
    parser.add_argument('-o', '--output', required=True, help='Folder to store new data format files.')
    parser.add_argument('-p', '--prefix', required=True, help='Prefix name of the new data format files.')
    return parser.parse_args()

def update_data(df: pd.DataFrame, now: datetime):
    df.drop(columns=[
        'other_tags', 'senso', 'rotonda', 'one_way', 'name_senso',
        'gis_osm_ro', 'gis_osm__1', 'gis_osm__2',
        'distanza in metri', 'speed km/h', 'tempo percorrenza in secondi',
        # from brindisi data
        'code', 'ref', 'oneway', 'maxspeed', 'layer', 'bridge', 'tunnel', 'POSIZIONE', 'path', 'other_tags'
        # from Chiamate Pisa Novembre 2024
        'day', 'time', 'daytime'
    ], inplace=True, errors='ignore')

    df.rename(columns={
        'output_distanza in metri': 'distance',
        'output_speed km/h': 'speed',
        'output_tempo percorrenza in secondi': 'travel_time',
        'lenght': 'length',
        # from brindisi data
        'fid': 'id',
        'fclass': 'highway',
        'startpoint': 'xy_start',
        'Endpoint': 'xy_end',
        'Distanza': 'length',
        # from Chiamate Pisa Novembre 2024
        'distance_meter': 'distance',
        'speed_km/h': 'speed',
        'travel_time_seconds': 'travel_time'
    }, inplace=True, errors='ignore')

    hour = int(now.strftime('%H'))
    daytime = ("day" if 6 <= hour < 20 else "evening" if 20 <= hour < 22 else "night")
    df['daytime'] = daytime

    if 'z_order' not in df.columns:
        df['z_order'] = 0
    df = df[['id', 'osm_id', 'name', 'highway', 'z_order', 'xy_start', 'xy_end', 'length', 'distance', 'speed', 'travel_time', 'daytime']]

    return df

if __name__ == "__main__":
    now = datetime.now()
    setup_logging('update_data', now)

    args = parse_args()

    if not os.path.isdir(args.input):
        logging.error(f"The input folder does not exist: {args.input}")
        sys.exit(1)
    
    if not os.path.isdir(args.output):
        os.makedirs(args.output, exist_ok=True)

    
    # from Chiamate Pisa Novembre 2024
    weekdays = {
        'Thursday': '07',
        'Friday': '08',
        'Saturday': '09',
        'Sunday': '10',
        'Monday': '11',
        'Tuesday': '12',
        'Wednesday': '13'
    }
    
    for filename in os.listdir(args.input):
        if filename.endswith(".csv"):
            fields = filename[:-4].split("_")

            weekday = fields[0]
            hour = fields[1]
            minute = fields[2]
            timestamp = f'202411{weekdays[weekday]} {hour}{minute}00'

            _now = datetime.strptime(timestamp, '%Y%m%d %H%M%S')
            output_filename = generate_output_filename(args.output, args.prefix, _now)

            input_filename = os.path.join(args.input, filename)

            df = read_csv_file(input_filename)
            df = update_data(df, _now)
            write_csv_file(df, output_filename)


    # from Chiamate July Pisa / Brindisi
    # for filename in os.listdir(args.input):
    #     if filename.endswith(".csv"):
    #         fields = filename.split("_")
    #         timestamp = fields[3] + ' ' + fields[4].split('.')[0]

    #         _now = datetime.strptime(timestamp, '%Y%m%d %H%M%S')
    #         output_filename = generate_output_filename(args.output, args.prefix, _now)

    #         input_filename = os.path.join(args.input, filename)

    #         df = read_csv_file(input_filename)
    #         df = update_data(df, _now)
    #         write_csv_file(df, output_filename)
