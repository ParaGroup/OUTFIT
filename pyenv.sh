#!/bin/bash

set -e  # Exit on any error

# CONFIG
MINICONDA_DIR="$HOME/miniconda3"
MINICONDA_INSTALLER="Miniconda3-latest-Linux-x86_64.sh"
if [[ "$OSTYPE" == "darwin"* ]]; then
    MINICONDA_INSTALLER="Miniconda3-latest-MacOSX-x86_64.sh"
fi
MINICONDA_URL="https://repo.anaconda.com/miniconda/$MINICONDA_INSTALLER"

# FUNCTIONS
install_miniconda() {
    echo "Downloading Miniconda installer..."
    curl -L -o "$MINICONDA_INSTALLER" "$MINICONDA_URL"

    echo "Installing Miniconda silently to $MINICONDA_DIR..."
    bash "$MINICONDA_INSTALLER" -b -p "$MINICONDA_DIR"

    echo "Cleaning up installer..."
    rm "$MINICONDA_INSTALLER"
}

# MAIN

# 1. Install Miniconda if needed
if [ -x "$MINICONDA_DIR/bin/conda" ]; then
    echo "Miniconda is already installed at $MINICONDA_DIR"
else
    install_miniconda
fi

# 2. Initialize conda (modify shell startup if needed)
eval "$("$MINICONDA_DIR/bin/conda" shell.bash hook)"

# 3. Check for environment.yml
if [ ! -f environment.yml ]; then
    echo "ERROR: environment.yml not found in current directory!"
    exit 1
fi

ENV_NAME=$(grep '^name:' environment.yml | awk '{print $2}')
if [ -z "$ENV_NAME" ]; then
    echo "ERROR: Could not extract environment name from environment.yml"
    exit 1
fi

# Check if environment already exists
if conda info --envs | awk '{print $1}' | grep -q "^$ENV_NAME$"; then
    echo "Environment '$ENV_NAME' already exists. Skipping creation."
else
    echo "Creating conda environment from environment.yml..."
    conda env create -f environment.yml
fi

# Activate the environment
echo "Activating environment: $ENV_NAME"
conda activate "$ENV_NAME"

echo "Environment '$ENV_NAME' is ready and activated."
