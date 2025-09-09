"""
Authors: Alberto Ottimo
Project: OUTFIT
Date: 2025-07-25
"""

from config import NP_FLOAT
import pandas as pd

INT_DTYPE    = 'int32'
FLOAT_DTYPE  = 'float32'
STRING_DTYPE = 'string'

SOUNDPLAN_OUTPUT_SCHEMA = {
    'Ricevitore'     : INT_DTYPE,
    'Sorgente'       : INT_DTYPE,
    'ora intervallo' : STRING_DTYPE,
    'X/m'            : STRING_DTYPE,
    'Y/m'            : STRING_DTYPE,
    'Z/m'            : STRING_DTYPE,
    '63Hz dB(A)'     : FLOAT_DTYPE,
    '125Hz dB(A)'    : FLOAT_DTYPE,
    '250Hz dB(A)'    : FLOAT_DTYPE,
    '500Hz dB(A)'    : FLOAT_DTYPE,
    '1000Hz dB(A)'   : FLOAT_DTYPE,
    '2000Hz dB(A)'   : FLOAT_DTYPE,
    '4000Hz dB(A)'   : FLOAT_DTYPE,
    '8000Hz dB(A)'   : FLOAT_DTYPE,
}

DATA_SCHEMA = {
    'id'          : INT_DTYPE,
    'osm_id'      : INT_DTYPE,
    'name'        : STRING_DTYPE,
    'highway'     : STRING_DTYPE,
    'xy_start'    : STRING_DTYPE,
    'xy_end'      : STRING_DTYPE,
    'length'      : FLOAT_DTYPE,
    'datetime'    : STRING_DTYPE,
    'daytime'     : STRING_DTYPE,
    'distance'    : FLOAT_DTYPE,
    'travel_time' : FLOAT_DTYPE,
    'speed'       : FLOAT_DTYPE,
}

MATRIX_SCHEMA = {
    'id'          : INT_DTYPE,
    'vehicle_type': STRING_DTYPE,
    'receiver'    : INT_DTYPE,
    'X/m'         : STRING_DTYPE,
    'Y/m'         : STRING_DTYPE,
    'Z/m'         : STRING_DTYPE,
    '63'          : FLOAT_DTYPE,
    '125'         : FLOAT_DTYPE,
    '250'         : FLOAT_DTYPE,
    '500'         : FLOAT_DTYPE,
    '1000'        : FLOAT_DTYPE,
    '2000'        : FLOAT_DTYPE,
    '4000'        : FLOAT_DTYPE,
    '8000'        : FLOAT_DTYPE,
}

STREET_PARAMS_SCHEMA = {
    'highway'     : STRING_DTYPE,
    'capacity'    : INT_DTYPE,
    'free_speed'  : FLOAT_DTYPE,
    'daytime'     : STRING_DTYPE,
    'alpha'       : FLOAT_DTYPE,
    'beta'        : FLOAT_DTYPE,
    'vehicle_type': STRING_DTYPE,
    'value'       : FLOAT_DTYPE,
}

FREQ_COEFFS_SCHEMA = {
    'vehicle_type': STRING_DTYPE,
    '63'          : STRING_DTYPE,
    '125'         : STRING_DTYPE,
    '250'         : STRING_DTYPE,
    '500'         : STRING_DTYPE,
    '1000'        : STRING_DTYPE,
    '2000'        : STRING_DTYPE,
    '4000'        : STRING_DTYPE,
    '8000'        : STRING_DTYPE,
}

CURVEA_SCHEMA = {
    '63'  : FLOAT_DTYPE,
    '125' : FLOAT_DTYPE,
    '250' : FLOAT_DTYPE,
    '500' : FLOAT_DTYPE,
    '1000': FLOAT_DTYPE,
    '2000': FLOAT_DTYPE,
    '4000': FLOAT_DTYPE,
    '8000': FLOAT_DTYPE,
}

VEHICLES_SCHEMA = {
    "id"              : INT_DTYPE,
    "osm_id"          : INT_DTYPE,
    "name"            : STRING_DTYPE,
    "highway"         : STRING_DTYPE,
    "xy_start"        : STRING_DTYPE,
    "xy_end"          : STRING_DTYPE,
    "length"          : FLOAT_DTYPE,
    "datetime"        : STRING_DTYPE,
    "daytime"         : STRING_DTYPE,
    "distance"        : INT_DTYPE,
    "travel_time"     : INT_DTYPE,
    "speed"           : INT_DTYPE,
    "capacity"        : INT_DTYPE,
    "free_speed"      : FLOAT_DTYPE,
    "alpha"           : FLOAT_DTYPE,
    "beta"            : FLOAT_DTYPE,
    "value"           : FLOAT_DTYPE,
    "travel_freespeed": FLOAT_DTYPE,
    "f1"              : INT_DTYPE,
    "f2"              : INT_DTYPE,
    "f3"              : INT_DTYPE,
    "f4"              : INT_DTYPE,
}

def sanitize_df(df: pd.DataFrame, schema: dict, drop: bool = True) -> pd.DataFrame:
    # Ensure all expected columns exist
    for col in schema:
        if col not in df.columns:
            raise ValueError(f"Missing expected column: {col}")

    # Drop unexpected columns
    if drop:
        df = df[[col for col in df.columns if col in schema]]

    # Enforce data types
    df = df.astype(schema, copy=False)

    return df