"""
Author: Alberto Ottimo
Project: OUTFIT
Date: 2025-08-06
"""

import os
import sys
import argparse
from process_functions import *
from datetime import datetime


attenuation_matrix_filename = ""
street_params_df      = pd.DataFrame()
freq_coeffs_df        = pd.DataFrame()
curve_A_df            = pd.DataFrame()
attenuation_matrix_df = pd.DataFrame()

def parse_args():
    """
    Parse command-line arguments.
    """
    parser = argparse.ArgumentParser(description="...") # TODO
    parser.add_argument('-i', '--input',  required=True,  help="Directory to all CSV file to process.")
    parser.add_argument('-a', '--matrix', required=True,  help="Path to the Noise Attenuation Matrix.")
    parser.add_argument('-o', '--output', required=True,  help="Directory to store output files.")
    parser.add_argument('-f', '--force' , required=False, help="Force rewrite output files.", action='store_true')
    parser.add_argument('-m', '--merge',  required=False, help="Merge all output to a single file.", action='store_true')
    return parser.parse_args()

@timer
def read_parameters():
    global street_params_df, freq_coeffs_df, curve_A_df, attenuation_matrix_df

    logging.info("Reading parameters files...")
    street_params_df      = read_file(street_params_filename, PARAMS_DIR)
    freq_coeffs_df        = read_file(freq_coeffs_filename, PARAMS_DIR)
    curve_A_df            = read_file(curve_A_filename, PARAMS_DIR)
    attenuation_matrix_df = read_file(attenuation_matrix_filename)

@timer
def preprocess_parameters():
    global street_params_df, freq_coeffs_df, attenuation_matrix_df

    logging.info("Preprocessing 'street_params', 'coeff_freq', and 'attenuation_matrix'...")
    street_params_df      = preprocess_street_params(street_params_df)
    freq_coeffs_df        = preprocess_freq_coeffs(freq_coeffs_df)
    attenuation_matrix_df = preproces_attenuation_matrix(attenuation_matrix_df)

@timer
def process_data(filename):
    global street_params_df, freq_coeffs_df, curve_A_df, attenuation_matrix_df

    logging.info("Reading input data...")
    data_df = read_file(filename)

    logging.info("Starting computation...")
    equivalent_flows_df      = equivalent_flows(data_df, street_params_df)
    sound_pressure_levels_df = sound_pressure_levels(equivalent_flows_df, freq_coeffs_df, curve_A_df)
    attenuated_df            = noise_attenuation(sound_pressure_levels_df, attenuation_matrix_df)
    energetic_sum_df         = energetic_sum(attenuated_df)

    return energetic_sum_df


@timer
def process_all_data(input_dir, output_dir, merge = False, force = False):

    # Variables for merged output
    output_merged_filepath = os.path.join(output_dir, 'merged.csv')
    merged_df = pd.DataFrame()

    for filename in os.listdir(input_dir):
        if filename.endswith(".csv"):
            fields = filename.split("-")
            timestamp_str = fields[-3] + ' ' + fields[-2]
            timestamp_dt = datetime.strptime(timestamp_str, '%Y%m%d %H%M%S')

            input_filepath = os.path.join(input_dir, filename)
            df = process_data(input_filepath)
            df['timestamp'] = timestamp_dt

            if merge:
                merged_df = pd.concat([merged_df, df])
            else:
                if os.path.isfile(filename):
                    if not force:
                        sys.exit(4)
                    else:
                        logging.debug(f"Overwriting file {filename}")
                        
                output_filepath = os.path.join(output_dir, filename)
                write_csv_file(df, output_filepath)

    if merge:
        if os.path.isfile(output_merged_filepath):
            if not force:
                sys.exit(4)
            else:
                logging.debug(f"Overwriting file {output_merged_filepath}")
        write_csv_file(merged_df, output_merged_filepath)


if __name__ == "__main__":
    now = datetime.now()
    setup_logging("process", now, debug=True)

    args = parse_args()

    if not os.path.isdir(args.input):
        logging.error(f"Input directory path does not exist: {args.input}")
        sys.exit(1)

    if not os.path.isfile(args.matrix):
        try:
            merge_file(args.matrix)
        except FileNotFoundError:
            logging.error(f"The Noise Attenuation matrix does not exists: {args.matrix}")
            sys.exit(2)
    else:
        attenuation_matrix_filename = str(args.matrix)

    if not os.path.isdir(args.output):
        logging.error(f"Output directory path does not exists: {args.output}")

    read_parameters()
    preprocess_parameters()
    process_all_data(args.input, args.output, args.merge, args.force)