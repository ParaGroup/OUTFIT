# OUTFIT
**OUTFIT - Dynamic Road Noise Maps Based on Crowdsourced Data and Represented in Digital Twins**

The **OUTFIT PRIN 2022** project aims to dynamically represent road traffic noise (RTN) in a **Digital Twin (DT)** model by optimizing the data flow related to noise levels and citizen perception.


## Overview
This repository provides tools to:
- Collect raw data via API calls to the **Google Maps Directions** service.
- Process this data to generate **perceived sound power** at receivers located on building facades in the area of interest.


# Installation
## Requirements
This project requires the following Python packages:
- python-dotenv
- requests
- numpy
- pyarrow
- pandas
- wxpython
- pyinstaller

It is recommended to install these packages inside a Python virtual environment using **conda** or **venv**.

You can find instructions to install Conda here: [Conda Installation](https://docs.conda.io/projects/conda/en/latest/user-guide/install/)
You can find instructions to install venv (built into Python 3) here: [venv Documentation](https://docs.python.org/3/library/venv.html)

Tip: You can use `pyenv.bat` (Windows) or `source pyenv.sh` (Linux/macOS) to automatically install Miniconda, set up the environment, and enter it.
Alternatively, you can use `bundle.bat` (Windows, Linux/macOS support coming soon) to generate a standalone execution file for the entire project.


## Using Conda
Once Conda is installed, create and activate a new environment with:

```bash
conda env create -f environment.yml
conda activate outfit
```

This will automatically install all required packages defined in `environment.yml`.


## Using venv
`venv` is a built-in Python module for creating isolated environments.
Using a virtual environment ensures that your project dependencies do not conflict with other Python projects on your system.
Steps to create a `venv`, install packages, and enter the environment:

### Windows CMD
```bash
python -m venv outfit
.\outfit\Scripts\activate
pip install -r requirements.txt
```

### Windows PowerShell
```bash
python -m venv outfit
.\outfit\Scripts\Activate.ps1
pip install -r requirements.txt
```

### macOS and Linux
```bash
python -m venv outfit
source outfit/bin/activate
pip install -r requirements.txt
```

# Usage
You can run the project in two ways:

1. **Download the executable**
   Download the `OUTFIT.exe` file and run it directly.

2. **Run with Python**
   Install the required packages (see [Installation](#installation)) and run the GUI with:
   ```bash
   python src/outfit.py


## Using the GUI
Once the GUI appears, you will need to provide the following information:
- `API Key`: your Google APIs key;
- `Prefix`: a name to identify your collected data;
- `data`: the path of the CSV file containing the streets for which data will be collected;
- `Data Range`: the date and time range over which the data will be collected.
- `Interval`: the time in minutes between two consecutive API calls while collecting street information.

After filling in all the required fields:
- Click `Start Schedule` to begin the data collection task.
- Click `Remove Schedules` to delete all scheduled tasks.