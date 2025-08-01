"""
Authors: Pasquale Gorrasi & Alberto Ottimo
Project: OUTFIT
Date: 2025-07-25
"""

import os
import sys
import argparse
from datetime import datetime
import requests
import pandas as pd
from dotenv import load_dotenv
from utils import *

def parse_args():
    """
    Parse command-line arguments.
    """
    parser = argparse.ArgumentParser(description="Collect data using Google Directions API.")
    parser.add_argument('-i', '--input',  required=True,  help="Path to input CSV file.")
    parser.add_argument('-d', '--dir',    required=False, help="Specify the directory to store the output CSV file.", default="")
    parser.add_argument('-p', '--prefix', required=True,  help="Prefix name of output CSV file.")
    return parser.parse_args()

def load_api_key() -> str:
    """
    Load Google Maps API key from .env file.
    """
    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("Google API key not found. Make sure .env contains GOOGLE_API_KEY.")
    return api_key

def call_directions_api(origin: str, destination: str, api_key: str) -> tuple[int, int, int]:
    """
    Call the Google Directions API and return distance (m), duration (s), and speed (km/h).
    """
    base_url = "https://maps.googleapis.com/maps/api/directions/json"
    params = {
        "origin": origin,
        "destination": destination,
        "key": api_key,
        "departure_time": "now"
    }

    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        data = response.json()

        leg = data['routes'][0]['legs'][0]
        distance = leg['distance']['value']
        duration = leg['duration_in_traffic']['value']
        if duration == 0:
            duration = 1
        speed = round((distance / duration) * 3.6)

        return distance, duration, speed
    except (requests.RequestException, KeyError, IndexError) as e:
        logging.warning(f"Failed to retrieve directions: {origin} -> {destination} | {e}")
        return 1, 1, 1


def enrich_with_directions(df: pd.DataFrame, now: datetime) -> pd.DataFrame:
    """
    Enrich the DataFrame `df` with distance (m), duration (s), and speed (km/h).
    """
    if 'xy_start' not in df.columns or 'xy_end' not in df.columns:
        raise ValueError("`df` must contain 'xy_start' and 'xy_end' columns.")

    api_key = load_api_key()
    
    hour = int(now.strftime('%H'))
    # Initialize new columns
    df['datetime'] = now
    df['daytime'] = ('day' if 6 <= hour < 20 else 'evening' if 20 <= hour < 22 else 'night')
    df['distance'] = 1
    df['travel_time'] = 1
    df['speed'] = 1

    for idx, row in df.iterrows():
        origin = str(row['xy_start'])
        destination = str(row['xy_end'])

        if pd.isna([origin, destination]).any():
            logging.warning(f"Skipping [{row['id']}, {row['name']}] with missing coordinates.")
            continue

        distance, duration, speed = call_directions_api(origin, destination, api_key)
        df.at[idx, 'distance'] = distance
        df.at[idx, 'travel_time'] = duration
        df.at[idx, 'speed'] = speed

    return df


if __name__ == "__main__":
    now = datetime.now()
    setup_logging('collect', now)

    args = parse_args()

    if not os.path.isfile(args.input):
        logging.error(f"The input file does not exist: {args.input}")
        sys.exit(1)

    if not (args.prefix and args.prefix.strip()):
        logging.error(f'The prefix has not been specified.')
        sys.exit(2)

    if not os.path.isdir(args.dir):
        logging.error(f"The output directory does not exist: {args.dir}")
        sys.exit(3)

    try:
        input_filename = args.input
        output_filename = generate_output_filename(args.dir, args.prefix, now)

        logging.info(f"Processing started: input={input_filename}, output={output_filename}")
        input_df = read_file(input_filename)
        output_df = enrich_with_directions(input_df, now)
        write_csv_file(output_df, output_filename)

    except Exception as e:
        logging.error("Fatal error occurred: {e}")
        raise
