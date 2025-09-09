"""
Author: Alberto Ottimo
Project: OUTFIT
Date: 2025-08-06
"""

import os
import glob
from datetime import datetime
import argparse
import pandas as pd
from utils import *
from config import *
from schemas import SOUNDPLAN_OUTPUT_SCHEMA, sanitize_df

# Sorgente = NaN possono essere cancellate le righe?
# Al variare di Z/m, sembra che i valori siano tutti uguali, e' corretto? (sia soundplan_export_periferia che ovviamente la matrice di abbattimento)
# TODO: Ci sono alcune righe con SType = 'Road' che non hanno nessun valore (li ho tolti)
# TODO: c'e' una riga in ogni RREC in cui Z/m == 0  (618 per RREC0008)

def parse_args():
    """
    Parse command-line arguments.
    """
    parser = argparse.ArgumentParser(description='Generate Noise Attenuation Matrix from SoundPlan csv files.')
    parser.add_argument('-i', '--input',   required=True,  help='Input directory of the SoundPlan csv files.')
    parser.add_argument('-l', '--LW100',   required=True,  help='Input of the LW100 csv/parquet file.')
    parser.add_argument('-o', '--output',  required=True,  help='Output filename (.parquet).')
    parser.add_argument('-v', '--verbose', required=False, help='Show statistics.', action='store_true', default=False)
    return parser.parse_args()

def read_csv_iso(filepath: str) -> pd.DataFrame:
    engine = 'pyarrow' if USE_PYARROW else 'c'
    return pd.read_csv(filepath, encoding='ISO-8859-1', sep=';', decimal=',', engine=engine)

def apply_rrec(df: pd.DataFrame, rrec: pd.DataFrame) -> pd.DataFrame:
    rrec = rrec.loc[:, ['RecNo', 'X/m', 'Y/m', 'Z/m']]

    # Set RecNo == 1 to the Z/m value of other RecNo
    zm_value = rrec.loc[rrec["RecNo"] != 1, "Z/m"].max()
    logging.warning(f'Setting `Z/m` = {zm_value} to row with `RecNo` == 1')
    rrec.loc[rrec["RecNo"] == 1, "Z/m"] = zm_value

    df = df.merge(rrec, how='left', on='RecNo', sort=False, copy=False)

    freq_cols = {f'FOT{f}' : f'{f}Hz dB(A)' for f in FREQUENCIES}
    freq_cols_list = list(freq_cols.keys())
    cols = {
        'RecNo' : 'Ricevitore',
        'SrcNo' : 'Sorgente',
        'ZBname' : 'ora intervallo',
        **freq_cols
    }

    mask = (
          (df["SType"] == "Road")
        & (df["ZBname"] != "Lden")
        & (df["ZBname"] != "LDit")
    )
    df = df.loc[mask]

    # Drop rows where all frequency columns are NaN
    df = df.dropna(subset=freq_cols_list, how='all')

    # Fill NaN values in freq_cols with -99999.0
    df[freq_cols_list] = df[freq_cols_list].fillna(-99999.0)

    df = df.rename(columns=cols)
    return sanitize_df(df, SOUNDPLAN_OUTPUT_SCHEMA)


@timer
def apply_LW100(df: pd.DataFrame, lw100: pd.DataFrame) -> pd.DataFrame:
    df = df[df['ora intervallo'] != 'Lden']
    df = df[df['ora intervallo'] != 'LDit']

    df_freq_cols = [f"{f}Hz dB(A)" for f in FREQUENCIES]
    lw_aligned = (
        lw100.set_index("vehicle_type")
        .reindex(df["ora intervallo"])[FREQUENCIES]
        .to_numpy()
    )

    df[df_freq_cols] = NP_FLOAT(df[df_freq_cols].to_numpy() - lw_aligned)
    df = df.fillna(NP_FLOAT(-99999)).reset_index(drop=True)
    return df

def apply_rroa(df: pd.DataFrame, rroa: pd.DataFrame) -> pd.DataFrame:
    rroa_min = rroa[["SrcNo", "Roadname"]]
    df = df.merge(rroa_min, left_on="Sorgente", right_on="SrcNo", how="inner", copy=False, sort=False)
    df["Sorgente"] = df["Roadname"]
    return sanitize_df(df, SOUNDPLAN_OUTPUT_SCHEMA)

def show_stats(df: pd.DataFrame):
    print('Dataframe info:')
    print(df.info())
    print("\nMissing values per column:")
    print(df.isnull().sum())

if __name__ == '__main__':
    now = datetime.now()
    setup_logging('attenuation_matrix', now)

    args = parse_args()

    if not os.path.isdir(args.input):
        logging.error(f"Input dir {args.input} does not exist.")
        sys.exit(1)

    if not os.path.isfile(args.LW100):
        logging.error(f"LW100 file {args.LW100} does not exist.")
        sys.exit(2)

    if not args.output.endswith('.parquet'):
        args.output += '.parquet'

    logging.info("Checking input files...")
    # RCFQ and RREC files
    files = sorted(glob.glob("*.csv", root_dir=args.input))
    rcfq_filenames = [f for f in files if f.startswith("RCFQ")]
    rcfq_filenames.sort()
    rrec_filenames = [f for f in files if f.startswith("RREC")]
    rrec_filenames.sort()

    if len(rcfq_filenames) != len(rrec_filenames):
        logging.error(f"Number of RCFQ files ({len(rcfq_filenames)}) does not match number of RREC files ({len(rrec_filenames)}).")
        sys.exit(3)

    for rcfq_file in rcfq_filenames:
        if rcfq_file.replace("RCFQ", "RREC") not in rrec_filenames:
            logging.error(f"RCFQ file {rcfq_file} does not have a matching RREC file.")
            sys.exit(4)

    # RROA file
    rroa_filename = [f for f in files if f.startswith("RROA")]
    if len(rroa_filename) != 1:
        logging.error(f"Expected exactly one RROA file, found {len(rroa_filename)}.")
        sys.exit(5)
    rroa_filepath = os.path.join(args.input, rroa_filename[0])

    # LW100 file
    if not os.path.isfile(args.LW100):
        logging.error(f"LW100 file {args.LW100} does not exist.")
        sys.exit(6)
    lw100_filepath = args.LW100


    df_list = []
    for rcfq_file, rrec_file in zip(rcfq_filenames, rrec_filenames):
        rcfq_path = os.path.join(args.input, rcfq_file)
        rrec_path = os.path.join(args.input, rrec_file)
        logging.info(f"Processing RCFQ file: {rcfq_path} with RREC file: {rrec_path}")
        df = read_csv_iso(rcfq_path)
        rrec = read_csv_iso(rrec_path)
        df = apply_rrec(df, rrec)
        df_list.append(df)

    df = pd.concat(df_list, ignore_index=True)

    logging.info("Reading LW100 and RROA files...")
    lw100_df = read_file(lw100_filepath)
    rroa_df = read_csv_iso(rroa_filepath)

    logging.info("Applying LW100...")
    df = apply_LW100(df, lw100_df)

    logging.info("Applying RROA...")
    df = apply_rroa(df, rroa_df)

    logging.info("Writing output file...")
    write_parquet_file(df, args.output)

    logging.info(f"Output written to {args.output}")

    if args.verbose:
        show_stats(df)