"""
Authors: Pasquale Gorrasi & Alberto Ottimo
Project: OUTFIT
Date: 2025-07-25
"""

import numpy as np

USE_PYARROW  = True
NP_FLOAT     = np.float32
NP_INT       = np.int32

FREQUENCIES_VALUES = [63, 125, 250, 500, 1000, 2000, 4000, 8000]
FREQUENCIES = list(map(str, FREQUENCIES_VALUES))
VEHICLE_COEFFICIENTS = {
    'f1': 1.0,  # light vehicles
    'f2': 2.0,  # medium-heavy vehicles
    'f3': 0.0,  # heavy vehicles (not present in urban streets)
    'f4': 0.5   # powered two-wheelers vehicles
}

# Mapping of `L` names to `f` names
L2F = {
    'Ld': 'f1',  # f1: Light Vehicles
    'Le': 'f2',  # f2: Medium-Heavy Vehicles
    'Lx': 'f3',  # f3: Heavy Vehicles (not present in urban streets)
    'Ln': 'f4'   # f4: Powered Two-Wheelers Vehicles
}

PARAMS_DIR = 'params'
STREET_PARAMS_FILENAME = "street_params.csv"
FREQ_COEFFS_FILENAME   = "freq_coeffs.csv"
CURVE_A_FILENAME       = "curve_A.csv"

SCHEDULE_PREFIX        = "outfit"
API_OUTPUT_DIRNAME     = "api_output"
PROCESSED_DATA_DIRNAME = "processed_data"