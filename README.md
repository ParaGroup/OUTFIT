# OUTFIT
**OUTFIT - Dynamic Road Noise Maps Based on Crowdsourced Data and Represented in Digital Twins**

The OUTFIT PRIN 2022 project aims to dynamically represent road traffic noise (RTN) in a Digital Twin (DT) model by optimizing the data flow related to noise levels and citizen perception.

## Overview
This repository is dedicated to developing the pipeline that, starting from raw data obtained via API calls to the Google Maps Directions service, provides an output matrix of the perceived sound power at receivers located on building facades in the area of interest.

# Installation
The project needs the following package installed:
- python-dotenv
- requests
- numpy
- pyarrow
- pandas

We suggest to install them in a Python environment with `conda` (see [Miniconda Installation](#Miniconda-Installation)) or `venv` (see [Python Venv Installation](Python-Venv-Installation)).

## Miniconda Installation
The following commands to install Miniconda3 on your system are taken from the [official documentation](https://docs.anaconda.com/miniconda/).
### Windows CMD
```bash
curl https://repo.anaconda.com/miniconda/Miniconda3-latest-Windows-x86_64.exe -o miniconda.exe
start /wait "" .\miniconda.exe /S
del miniconda.exe

# After installing, open the “Anaconda Powershell Prompt (miniconda3)” and
# create a new environment from the environment.yml file
conda env create -f environment.yml
```

### Windows PowerShell
```bash
curl https://repo.anaconda.com/miniconda/Miniconda3-latest-Windows-x86_64.exe -o miniconda.exe
Start-Process -FilePath ".\miniconda.exe" -ArgumentList "/S" -Wait
del miniconda.exe

# After installing, open the “Anaconda Prompt (miniconda3)” and
# create a new environment from the environment.yml file
conda env create -f environment.yml
```

### macOS
```bash
mkdir -p ~/miniconda3
curl https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-arm64.sh -o ~/miniconda3/miniconda.sh
bash ~/miniconda3/miniconda.sh -b -u -p ~/miniconda3
rm ~/miniconda3/miniconda.sh

# Initialize miniconda for bash or zsh shells:
~/miniconda3/bin/conda init bash
# or
~/miniconda3/bin/conda init zsh

# Close and reopen your terminal to activate conda and
# create a new environment from the environment.yml file
conda env create -f environment.yml
```

### Linux
```bash
mkdir -p ~/miniconda3
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O ~/miniconda3/miniconda.sh
bash ~/miniconda3/miniconda.sh -b -u -p ~/miniconda3
rm ~/miniconda3/miniconda.sh

# Initialize miniconda for bash or zsh shells:
~/miniconda3/bin/conda init bash
# or
~/miniconda3/bin/conda init zsh

# Close and reopen your terminal to activate conda and
# create a new environment from the environment.yml file
conda env create -f environment.yml
```

## Python Venv Installation
The following commands to create a Python virtual environment are taken from the [official documentation](https://docs.python.org/3/library/venv.html).

Before creating the virtual environment, make sure you have [cloned the repository](#clone-the-repository) and `cd` into it (e.g., `cd ~/OUTFIT`).

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