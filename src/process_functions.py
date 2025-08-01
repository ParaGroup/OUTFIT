from utils import *
import numpy as np
import pandas as pd


#------------------------------------------------------------------------------
#
# Constants
#
#------------------------------------------------------------------------------

ID_JOIN = 'osm_id' # osm_id per Pisa, id per Brindisi?
freqs = [f'{freq}' for freq in [63, 125, 250, 500, 1000, 2000, 4000, 8000]]

f1_coeff = 1.0 # f1: light vehicles
f2_coeff = 2.0 # f2: medium-heavy vehicles
f3_coeff = 0.0 # f3: heavy vehicles (not present in urban streets)
f4_coeff = 0.5 # f4: powered two-wheelers vehicles


#------------------------------------------------------------------------------
#
# Preprocess functions
#
#------------------------------------------------------------------------------

@timer
def preprocess_street_params(
    df: pd.DataFrame
) -> pd.DataFrame:
    """
    Preprocesses street parameter data for different vehicle types.

    This function performs the following operations:
    - Converts 'free_speed' from km/h to m/s.
    - Computes a weighted sum of coefficients (f1,f2,f3,f4) and normalizes them.
    - Add to the DataFrame the 'vehicle_type' and 'value' columns.

    Args:
        df (pd.DataFrame): Input DataFrame with street parameters and vehicle type coefficients.

    Returns:
        pd.DataFrame: DataFrame with normalized (f1,f2,f3,f4).
    """
        
    # Convert free_speed from km/h to m/s
    df['free_speed'] /= 3.6

    # Coefficients mapping
    coeffs = {'f1': f1_coeff, 'f2': f2_coeff, 'f3': f3_coeff, 'f4': f4_coeff}

    # Compute row-wise weighted sum
    weight_sum = sum(df[k] * coeffs[k] for k in coeffs)

    # Normalize each f-column
    for k in coeffs:
        df[k] = df[k] * coeffs[k] / weight_sum # TODO: check if this line is correct

    # Melt the DataFrame
    id_vars = ['highway', 'capacity', 'free_speed', 'daytime', 'alpha', 'beta']
    value_vars = list(coeffs.keys())

    return pd.melt(df, id_vars=id_vars, value_vars=value_vars,
                   var_name='vehicle_type', value_name='value')

@timer
def preprocess_freq_coeffs(
    df: pd.DataFrame
) -> pd.DataFrame:
    """
    Parses semicolon-separated frequency coefficient into lists of floats.

    This function processes frequency columns containing string-encoded lists
    of numbers, converting them into actual lists of floats.

    Args:
        df (pd.DataFrame): DataFrame containing frequency coefficient strings.

    Returns:
        pd.DataFrame: DataFrame with frequency columns converted to lists of floats.
    """
    for freq in freqs:
        df[freq] = df[freq].str.split(';').apply(lambda lst: list(map(float, lst)))
    return df

@timer
def preproces_attenuation_matrix(
    df: pd.DataFrame
) -> pd.DataFrame:
    """
    Preprocesses the noise attenuation matrix DataFrame by renaming columns and
    mapping vehicle type labels.

    Operations performed:
    - Renames frequency columns (e.g., '500Hz dB(A)') to their numeric form
      (e.g., '500').
    - Renames metadata columns 'Ricevitore', 'Sorgente', and 'ora intervallo'
      into 'receiver', 'id' or 'id_osm', and 'vehicle_type'.  
    - Maps (Ld, Le, Lx, and Ln) columns (they were used as workaround to store
      standardized Vehicle Types codes) into (f1, f2, f3, f4).

    Args:
        df (pd.DataFrame): DataFrame with raw noise attenuation data.

    Returns:
        pd.DataFrame: Cleaned and standardized DataFrame ready for analysis.
    """

    cols = {f'{f}Hz dB(A)' : f'{f}' for f in freqs}
    cols.update({
        'Ricevitore': 'receiver',
        'Sorgente': ID_JOIN,
        'ora intervallo': 'vehicle_type',
    })
    df.rename(columns=cols, inplace=True)

    l2f = {
        'Ld': 'f1',  # f1: Light Vehicles
        'Le': 'f2',  # f2: Medium-Heavy Vehicles
        'Lx': 'f3',  # f3: Heavy Vehicles (not present in urban streets)
        'Ln': 'f4'   # f4: Powered Two-Wheelers Vehicles
    }
    df['vehicle_type'] = df['vehicle_type'].replace(l2f)
    return df


#------------------------------------------------------------------------------
#
# Execute functions
#
#------------------------------------------------------------------------------

@timer
def equivalent_flows(
    df: pd.DataFrame,
    street_params_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Modifies `df` DataFrame by adding a 'num_vehicles' column based on travel
    time and street parameters.

    - Computes free-speed travel time.
    - Calculates flow factor safely (avoids invalid values).
    - Multiplies flow by vehicle-type weights ('value').
    - Adds result as 'num_vehicles' (integer).

    Args:
        df (pd.DataFrame): DataFrame with traffic data (must include 'highway','daytime', 'distance', 'travel_time').
        street_params_df (pd.DataFrame): DataFrame with corresponding street parameters.
    """
    # Merge in-place using index alignment (adds columns to df)
    merged = df.merge(street_params_df, on=['highway', 'daytime'], how='left', sort=False, copy=False)

    # Compute free-speed travel time
    merged['travel_freespeed'] = merged['distance'] / merged['free_speed']

    # Compute flow factor safely
    with np.errstate(divide='ignore', invalid='ignore'):
        ratio = merged['travel_time'] / merged['travel_freespeed'] - 1
        base = ratio / merged['alpha']
        base = base.clip(lower=0)  # Ensure base >= 0
        flow_factor = base ** (1 / merged['beta'])

    # Compute number of vehicles
    merged['num_vehicles'] = (merged['capacity'] * flow_factor * merged['value']).astype(int)

    # Drop useless columns
    merged.drop(columns=[
        'highway', 'distance', 'daytime', 'capacity', 'free_speed', 'alpha', 'beta', 'value', 'travel_freespeed'
    ], inplace=True)
    return merged

def compute_LwR(Ar, Br, speed):
    return Ar + Br * np.log10(speed / 70)

def compute_LwP(Ap, Bp, speed):
    return Ap + Bp * (speed - 70) / 70

def compute_Lwim(LwR, LwP):
    return 10 * np.log10(10**(LwR / 10) + 10**(LwP / 10))

def compute_Lw(Ar, Br, Ap, Bp, num_vehicles, speed):
    if num_vehicles <= 0:
        return 0
    LwR = compute_LwR(Ar, Br, speed)
    LwP = compute_LwP(Ap, Bp, speed)
    Lwim = compute_Lwim(LwR, LwP)
    return Lwim + 10 * np.log10(num_vehicles / (1000 * speed))

@timer
def sound_pressure_levels(
    df: pd.DataFrame,
    coeff_freq_df: pd.DataFrame,
    curve_A_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Computes weighted Sound Power Levels (SPLs) for each row and frequency band.

    Args:
        df (pd.DataFrame): Contains 'vehicle_type', 'speed', 'num_vehicles', and location data.
        coeff_freq_df (pd.DataFrame): Maps each vehicle type to coefficients for each frequency band.
                                      Each frequency column is a list of 4 coefficients: [Ar, Br, Ap, Bp].
        curve_A_df (pd.DataFrame): A-weighting correction values, one row, with each frequency band.

    Returns:
        pd.DataFrame: Same structure as `df`, with SPLs per frequency and A-weighting applied.
    """

    merged = df.merge(coeff_freq_df, on='vehicle_type')

    for f in freqs:
        merged[f] = merged.apply(lambda x: compute_Lw(x[f][0], x[f][1], x[f][2], x[f][3], x['num_vehicles'], x['speed']), axis=1) + curve_A_df[f].values[0]

    merged.drop(columns=[
        'speed', 'num_vehicles'
    ], inplace=True)
    return merged

@timer
def noise_attenuation(
    df: pd.DataFrame,
    noise_attenuation_matrix_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Applies precomputed noise attenuation corrections to Sound Pressure Levels
    (SPLs) contained in `df`.

    Merges the SPLs with the noise attenuation matrix based on Receiver ID and
    vehicle type, and adds attenuation values to the SPLs per frequency.

    Args:
        df (pd.DataFrame): DataFrame containing SPL values per frequency.
        noise_attenuation_matrix_df (pd.DataFrame): DataFrame with attenuation values per frequency.

    Returns:
        pd.DataFrame: Updated SPL DataFrame with attenuation applied.
    """
    merged = df.merge(noise_attenuation_matrix_df, on=[ID_JOIN, 'vehicle_type'], suffixes=(None, '_r'))

    for f in freqs:
        merged[f] = merged[f].fillna(0) + merged[f'{f}_r'].fillna(0)
    
    merged.drop(columns=[f'{f}_r' for f in freqs])
    return merged


@timer
def energetic_sum(
    df: pd.DataFrame
) -> pd.DataFrame:
    """
    Computes the energetic sum of Sound Pressure Levels (SPLs) per receiver
    across frequency bands.

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
        return 10.0 ** (db / 10.0)

    def power_to_db(power):
        return 10.0 * np.log10(power)
    
    # Ensure no negative values before conversion
    df[freqs] = df[freqs].clip(lower=0)

    # Convert from dB to power
    df[freqs] = db_to_power(df[freqs])

    # Aggregate by receiver
    agg = df.groupby('receiver').agg({
        'X/m': 'first',
        'Y/m': 'first',
        **{f: 'sum' for f in freqs}
    })

    # Compute total SPL from summed power across all freqs
    agg['total_db'] = power_to_db(agg[freqs].sum(axis=1))

    # Convert frequency columns back to dB
    agg[freqs] = power_to_db(agg[freqs])

    return agg.reset_index()
