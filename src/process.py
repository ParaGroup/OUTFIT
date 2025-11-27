"""
Authors: Pasquale Gorrasi & Alberto Ottimo
Project: OUTFIT
Date: 2025-07-25
"""

import os
import glob
from datetime import datetime
import argparse
import numpy as np
import pandas as pd
from utils import *
from config import *
from schemas import *


class Pipeline:
    def __init__(self,
                 attenuation_matrix_filepath: str,
                 street_params_filepath: str,
                 freq_coeffs_filepath: str,
                 curveA_filepath: str):
        print("Initializing Pipeline...")
        self.setup_attenuation_matrix(attenuation_matrix_filepath)
        print("Attenuation matrix loaded.")
        self.setup_street_params(street_params_filepath)
        print("Street parameters loaded.")
        self.setup_freq_coeffs(freq_coeffs_filepath)
        print("Frequency coefficients loaded.")
        self.setup_curveA(curveA_filepath)
        print("Curve A loaded.")

    @timer
    def setup_attenuation_matrix(self, filepath: str):
        """
        Setup and preprocesses the noise attenuation matrix DataFrame by renaming columns and mapping vehicle type labels.

        Operations performed:
        - Renames frequency columns (e.g., '500Hz dB(A)') to their numeric form (e.g., '500').
        - Renames metadata columns 'Ricevitore', 'Sorgente', and 'ora intervallo' into 'receiver', 'id' or 'id_osm', and 'vehicle_type'.
        - Maps (Ld, Le, Lx, and Ln) columns (they were used as workaround to store standardized Vehicle Types codes) into (f1, f2, f3, f4).
        """

        cols = {
            'Ricevitore': 'receiver',
            'Sorgente': 'id',
            'ora intervallo': 'vehicle_type',
            **{f'{f}Hz dB(A)' : f'{f}' for f in FREQUENCIES}
        }

        df = read_file(filepath)
        df.rename(columns=cols, inplace=True)
        df['vehicle_type'] = df['vehicle_type'].replace(L2F)
        self.attenuation_matrix_df = sanitize_df(df, MATRIX_SCHEMA)


    @timer
    def setup_street_params(self, filepath: str):
        """
        Setup and preprocesses street parameter data for different vehicle types.

        This function performs the following operations:
        - Converts 'free_speed' from km/h to m/s.
        - Computes a weighted sum of coefficients (f1,f2,f3,f4) and normalizes them.
        - Add to the DataFrame the 'vehicle_type' and 'value' columns.
        """

        df = read_file(filepath)

        # Convert km/h to m/s
        df['free_speed'] = (df['free_speed'] / 3.6).astype(NP_FLOAT)

        # Normalize each f-column
        weight_sum = sum(df[k] * VEHICLE_COEFFICIENTS[k] for k in VEHICLE_COEFFICIENTS)
        for k in VEHICLE_COEFFICIENTS:
            df[k] = df[k] / weight_sum

        # Melt the DataFrame (for each row generate f1, f2, f3, f4 rows)
        id_vars = ['highway', 'capacity', 'free_speed', 'daytime', 'alpha', 'beta']
        value_vars = list(VEHICLE_COEFFICIENTS.keys())
        df = pd.melt(df,
                     id_vars=id_vars,
                     value_vars=value_vars,
                     var_name='vehicle_type',
                     value_name='value')

        self.street_params_df = sanitize_df(df, STREET_PARAMS_SCHEMA)

    @timer
    def setup_freq_coeffs(self, filepath: str):
        """
        Setup and preprocess frequency coefficients by converting string-encoded list of frequency into actual lists of floats.
        """

        df = read_file(filepath)
        self.freq_coeffs_df = sanitize_df(df, FREQ_COEFFS_SCHEMA)
        for f in FREQUENCIES:
            self.freq_coeffs_df[f] = self.freq_coeffs_df[f].str.split(';').apply(lambda lst: list(map(NP_FLOAT, lst)))

    @timer
    def setup_curveA(self, filepath):
        self.curveA_df = read_file(filepath)
        self.curveA_df = sanitize_df(self.curveA_df, CURVEA_SCHEMA)

    @timer
    def read_data(self, filepath, override_highway: str = '') -> pd.DataFrame:
        df = read_file(filepath)
        df = sanitize_df(df, DATA_SCHEMA)

        if override_highway:
            df['highway'] = override_highway

        return df

    @timer
    def equivalent_flows(self, df: pd.DataFrame, vehicles_filename: str = '') -> pd.DataFrame:
        """
        Modifies input DataFrame by adding a 'num_vehicles' column based on travel time and street parameters.

        - Computes free-speed travel time.
        - Calculates flow factor safely (avoids invalid values).
        - Multiplies flow by vehicle-type weights ('value').
        - Adds result as 'num_vehicles' (integer).

        Args:
            df (pd.DataFrame): DataFrame with traffic data (must include 'highway','daytime', 'distance', 'travel_time').
            street_params_df (pd.DataFrame): DataFrame with corresponding street parameters.
        """

        merged = df.merge(self.street_params_df, how='left', on=['highway', 'daytime'], sort=False, copy=False)

        merged['travel_freespeed'] = merged['distance'] / merged['free_speed']
        with np.errstate(divide='ignore', invalid='ignore'):
            ratio = merged['travel_time'] / merged['travel_freespeed'] - NP_FLOAT(1)
            base = ratio / merged['alpha']
            base = base.clip(lower=0)  # Ensure base >= 0
            flow_factor = base ** (1 / merged['beta'])

        # Compute number of vehicles for each veichle_type (f1, f2, f3, f4)
        merged['num_vehicles'] = (merged['capacity'] * flow_factor * merged['value']).fillna(0).astype(NP_INT)

        if vehicles_filename:
            vehicles_df = merged.pivot_table(index=['id'], columns='vehicle_type', values='num_vehicles', fill_value=0)
            final_df = merged.drop(columns=['vehicle_type', 'num_vehicles']).drop_duplicates('id')
            final_df = final_df.merge(vehicles_df, on='id', how='left')
            final_df = sanitize_df(final_df, VEHICLES_SCHEMA)
            write_csv_file(final_df, vehicles_filename)

        # Drop useless columns
        cols = ['highway', 'distance', 'daytime', 'capacity', 'free_speed', 'alpha', 'beta', 'value', 'travel_freespeed']
        merged.drop(columns=cols, inplace=True)
        return merged

    @staticmethod
    def compute_LwR(Ar, Br, speed):
        return Ar + Br * np.log10(speed / 70.0)

    @staticmethod
    def compute_LwP(Ap, Bp, speed):
        return Ap + Bp * (speed - 70.0) / 70.0

    @staticmethod
    def compute_Lwim(LwR, LwP):
        return 10.0 * np.log10(10.0**(LwR / 10.0) + 10.0**(LwP / 10.0))

    @staticmethod
    def compute_Lw(Ar, Br, Ap, Bp, num_vehicles, speed):
        if num_vehicles <= 0:
            return 0
        LwR = Pipeline.compute_LwR(Ar, Br, speed)
        LwP = Pipeline.compute_LwP(Ap, Bp, speed)
        Lwim = Pipeline.compute_Lwim(LwR, LwP)
        return NP_FLOAT(Lwim + 10.0 * np.log10(num_vehicles / (1000.0 * speed)))

    @timer
    def sound_pressure_levels(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Computes weighted Sound Power Levels (SPLs) for each row and frequency band.

        Args:
            df (pd.DataFrame): Dataframe containing 'vehicle_type', 'speed', 'num_vehicles', and location data.

        Returns:
            pd.DataFrame: Same structure as `df`, with SPLs per frequency and A-weighting applied.
        """

        merged = df.merge(self.freq_coeffs_df, on='vehicle_type', sort=False, copy=False)
        for f in FREQUENCIES:
            merged[f] = merged.apply(lambda x: Pipeline.compute_Lw(x[f][0], x[f][1], x[f][2], x[f][3], x['num_vehicles'], x['speed']), axis=1) + self.curveA_df[f].values[0]
        merged.drop(columns=['speed', 'num_vehicles'], inplace=True)
        return merged

    @timer
    def noise_attenuation(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Applies precomputed noise attenuation corrections to Sound Pressure Levels (SPLs) contained in `df`.

        Merges the SPLs with the noise attenuation matrix based on Receiver `id` and `vehicle type`, and adds attenuation values to the SPLs per frequency.

        Args:
            df (pd.DataFrame): DataFrame containing SPL values per frequency.

        Returns:
            pd.DataFrame: Updated SPL DataFrame with attenuation applied.
        """
        merged = df.merge(self.attenuation_matrix_df, on=['id', 'vehicle_type'], suffixes=(None, '_r'), sort=False, copy=False)
        for f in FREQUENCIES:
            merged[f] = merged[f] + merged[f'{f}_r']
        merged.drop(columns=[f'{f}_r' for f in FREQUENCIES], inplace=True)
        return merged

    @timer
    def energetic_sum(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Computes the energetic sum of Sound Pressure Levels (SPLs) per receiver across frequency bands.

        Steps:
        - Converts dB values to power.
        - Aggregates power values per receiver using sum.
        - Converts summed power back to dB (both per frequency and total).
        - Preserves spatial coordinates ('X/m', 'Y/m') and returns one row per receiver.

        Args:
            df (pd.DataFrame): DataFrame with SPL values per frequency and metadata.

        Returns:
            pd.DataFrame: Aggregated SPL per receiver with total dB and per-frequency dB values.
        """
        def db_to_power(db):
            return NP_FLOAT(10) ** (db / NP_FLOAT(10))

        def power_to_db(power):
            return NP_FLOAT(10) * np.log10(power)

        # Ensure no negative values before conversion
        df[FREQUENCIES] = df[FREQUENCIES].clip(lower=0.0)
        df[FREQUENCIES] = db_to_power(df[FREQUENCIES])

        # Aggregate by receiver
        agg = df.groupby(['receiver', 'X/m', 'Y/m', 'Z/m']).agg({
            **{f: 'sum' for f in FREQUENCIES}
        })

        # Compute total SPL from summed power across all FREQUENCIES
        agg['total_db'] = power_to_db(agg[FREQUENCIES].sum(axis=1))
        agg[FREQUENCIES] = power_to_db(agg[FREQUENCIES])

        return agg.reset_index()

    def run(self, df, vehicles_filepath: str = '') -> pd.DataFrame:
        eq_flows_df   = self.equivalent_flows(df, vehicles_filepath)
        spl_df        = self.sound_pressure_levels(eq_flows_df)
        attenuated_df = self.noise_attenuation(spl_df)
        esum          = self.energetic_sum(attenuated_df)
        return esum

    def execute_file(self,
                     input_filepath: str,
                     output_filepath: str,
                     vehicles_path: str = '',
                     override_highway: str = ''):

        logging.info(f'Processing file: f{input_filepath}')

        vehicles_filepath = vehicles_path
        if vehicles_path and os.path.isdir(vehicles_path):
            vehicles_filepath = os.path.join(vehicles_path, 'vehicles-' + filename_from_filepath(input_filepath))

        input_df = self.read_data(input_filepath, override_highway)
        output_df = self.run(input_df, vehicles_filepath)

        ts = get_timestamp_from_filename(input_filepath)
        output_df['timestamp'] = ts

        write_csv_file(output_df, output_filepath)

    def execute_dir(self,
                    input_dirpath: str,
                    output_dirpath: str,
                    vehicles_dirpath: str = '',
                    merge: bool = False,
                    override_highway: str = ''):

        files = sorted(glob.glob("*.csv", root_dir=input_dirpath))
        merged_ts = get_timestamp_from_filename(files[0])
        merged_filepath = generate_merged_filepath(output_dirpath, merged_ts)

        for f in files:
            ts = get_timestamp_from_filename(f)
            input_filepath = os.path.join(input_dirpath, f)

            logging.info(f'Processing: f{input_filepath}')

            input_df = self.read_data(input_filepath, override_highway)

            vehicles_filepath = vehicles_dirpath
            if vehicles_dirpath and os.path.isdir(vehicles_dirpath):
                vehicles_filepath = os.path.join(vehicles_dirpath, 'vehicles-' + f)

            output_df = self.run(input_df, vehicles_filepath)
            output_df['timestamp'] = ts

            if merge:
                file_not_exists = not os.path.exists(merged_filepath)
                append_csv_file(output_df, merged_filepath, file_not_exists)
            else:
                output_filepath = os.path.join(output_dirpath, f)
                write_csv_file(output_df, output_filepath)

    def execute(self,
                input_path: str,
                output_path: str,
                vehicles_path: str = '',
                merge: bool = False,
                override_highway: str = ''):

        if not input_path:
            message = "input_path is empty!"
            logging.error(message)
            raise RuntimeError(message)

        if not output_path:
            message = "output_path is empty!"
            logging.error("output_path is empty!")
            raise RuntimeError(message)


        if os.path.isfile(input_path):
            if os.path.isdir(output_path):
                message = f"output_path ({output_path}) is a directory! Please provide a filepath!"
                logging.error(message)
                raise RuntimeError(message)

            self.execute_file(input_path, output_path, vehicles_path, override_highway)

        elif os.path.isdir(input_path):
            if not vehicles_path:
                message = "vehicles_path is empty!"
                logging.error(message)
                raise RuntimeError(message)

            if not os.path.exists(output_path):
                os.mkdir(output_path)

            if not os.path.exists(vehicles_path):
                os.mkdir(vehicles_path)

            self.execute_dir(input_path, output_path, vehicles_path, merge, override_highway)

        else:
            message = f"input_path ({input_path}) is not a file/directory!"
            logging.error(message)
            raise RuntimeError(message)


def parse_args():
    """
    Parse command-line arguments.
    """
    parser = argparse.ArgumentParser(description="...") # TODO
    parser.add_argument('-i', '--input',            required=True,  help="Path to input file or directory. If it is a directory, all CSV files will be processed. See `--merge` to output a single file.")
    parser.add_argument('-o', '--output',           required=True,  help="Name of output file or directory. It can be a directory only when `--input` is a directory and `--merge` is not set.")
    parser.add_argument('-a', '--matrix',           required=True,  help="Path to the Attenuation Matrix.")
    parser.add_argument('-s', '--street_params',    required=False, help="Path to the Street Parameters file.")
    parser.add_argument('-f', '--freq_coeffs',      required=False, help="Path to the Frequency Coefficients file.")
    parser.add_argument('-c', '--curveA',           required=False, help="Path to the Curve A file.")
    parser.add_argument('-v', '--vehicles',         required=False, help="Name of output file or directory for vehicles data. If `--input` is a directory, it must be a directory too.")
    parser.add_argument('-x', '--override_highway', required=False, help="Override 'highway' field in input data with the provided value.")
    parser.add_argument('-m', '--merge',            required=False, help="Merge all output to a single file.", action='store_true')
    return parser.parse_args()


if __name__ == "__main__":
    now = datetime.now()
    setup_logging("process", now, debug=True)

    args = parse_args()

    input_path                  = args.input
    output_path                 = args.output
    attenuation_matrix_filepath = args.matrix
    street_params_filepath      = os.path.join(PARAMS_DIR, STREET_PARAMS_FILENAME)
    freq_coeffs_filepath        = os.path.join(PARAMS_DIR, FREQ_COEFFS_FILENAME)
    curveA_filepath             = os.path.join(PARAMS_DIR, CURVE_A_FILENAME)
    vehicles_path               = args.vehicles
    is_merge                    = args.merge

    try:
        if args.street_params:
            street_params_filepath = args.street_params

        if args.freq_coeffs:
            freq_coeffs_filepath = args.freq_coeffs

        if args.curveA:
            curveA_filepath = args.curveA

        pipeline = Pipeline(attenuation_matrix_filepath,
                            street_params_filepath,
                            freq_coeffs_filepath,
                            curveA_filepath)
        pipeline.execute(input_path, output_path, vehicles_path, is_merge, args.override_highway)
    except Exception as e:
        logging.error(f"Pipeline error: {e}")