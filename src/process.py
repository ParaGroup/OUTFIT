"""
Authors: Pasquale Gorrasi & Alberto Ottimo
Project: OUTFIT
Date: 2025-07-25
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
    parser.add_argument('-i', '--input',  required=True,  help="Path to input CSV file.")
    parser.add_argument('-a', '--matrix', required=True,  help="Path to the Attenuation Matrix.")
    parser.add_argument('-s', '--street_params', required=False,  help="Path to the Street Parameters file.")
    parser.add_argument('-f', '--freq_coeffs', required=False,  help="Path to the Frequency Coefficients file.")
    parser.add_argument('-c', '--curve_A', required=False,  help="Path to the Curve A file.")
    parser.add_argument('-o', '--output', required=True,  help="Name of output file.")
    parser.add_argument('--force' , required=False, help="Force rewrite output file.", action='store_true')
    return parser.parse_args()

@timer
def read_parameters(
        matrix_filename: str,
        street_params_filename: str,
        freq_coeffs_filename: str,
        curve_A_filename: str,
    ):
    global street_params_df, freq_coeffs_df, curve_A_df, attenuation_matrix_df

    logging.info("Reading parameters files...")
    street_params_df      = read_file(street_params_filename)
    freq_coeffs_df        = read_file(freq_coeffs_filename)
    curve_A_df            = read_file(curve_A_filename)
    attenuation_matrix_df = read_file(matrix_filename)

@timer
def preprocess_parameters():
    global street_params_df, freq_coeffs_df, attenuation_matrix_df

    logging.info("Preprocessing 'street_params', 'coeff_freq', and 'attenuation_matrix'...")
    street_params_df      = preprocess_street_params(street_params_df)
    freq_coeffs_df        = preprocess_freq_coeffs(freq_coeffs_df)
    attenuation_matrix_df = preproces_attenuation_matrix(attenuation_matrix_df)

@timer
def process_data(
    input_filename: str,
    matrix_filename: str,
    street_params_filename: str,
    freq_coeffs_filename: str,
    curve_A_filename: str,
    output_filename: str,
    overwrite: bool = False):
    global street_params_df, freq_coeffs_df, curve_A_df, attenuation_matrix_df, attenuation_matrix_filename

    if not os.path.isfile(input_filename):
        logging.error(f"The input file does not exist: {input_filename}")
        sys.exit(1)

    if not os.path.isfile(matrix_filename):
        try:
            merge_file(matrix_filename)
        except FileNotFoundError:
            logging.error(f"The Noise Attenuation matrix does not exists: {matrix_filename}")
            sys.exit(2)
    else:
        attenuation_matrix_filename = str(matrix_filename)

    if not street_params_filename:
        street_params_filename = os.path.join(PARAMS_DIR, STREET_PARAMS_FILENAME)
    else:
        if not os.path.isfile(street_params_filename):
            logging.error(f"The Street Parameters file does not exist: {street_params_filename}")
            sys.exit(3)

    if not freq_coeffs_filename:
        freq_coeffs_filename = os.path.join(PARAMS_DIR, FREQ_COEFFS_FILENAME)
    else:
        if not os.path.isfile(freq_coeffs_filename):
            logging.error(f"The Frequency Coefficients file does not exist: {freq_coeffs_filename}")
            sys.exit(4)

    if not curve_A_filename:
        curve_A_filename = os.path.join(PARAMS_DIR, CURVE_A_FILENAME)
    else:
        if not os.path.isfile(curve_A_filename):
            logging.error(f"The Curve A file does not exist: {curve_A_filename}")
            sys.exit(5)

    if os.path.isfile(output_filename):
        if not overwrite:
            logging.error(f"The file {output_filename} already exists! Use `--force` to overwrite it.")
            sys.exit(6)
        else:
            logging.debug(f"Overwriting file {output_filename}")

    read_parameters(matrix_filename, street_params_filename, freq_coeffs_filename, curve_A_filename)
    preprocess_parameters()

    logging.info("Reading input data...")
    data_df = read_file(input_filename)

    logging.info("Starting computation...")
    equivalent_flows_df      = equivalent_flows(data_df, street_params_df)
    sound_pressure_levels_df = sound_pressure_levels(equivalent_flows_df, freq_coeffs_df, curve_A_df)
    attenuated_df            = noise_attenuation(sound_pressure_levels_df, attenuation_matrix_df)
    energetic_sum_df         = energetic_sum(attenuated_df)

    write_csv_file(energetic_sum_df, output_filename)


if __name__ == "__main__":
    now = datetime.now()
    setup_logging("process", now, debug=True)

    args = parse_args()
    process_data(args.input, args.matrix, args.street_params, args.freq_coeffs, args.curve_A, args.output, args.force)