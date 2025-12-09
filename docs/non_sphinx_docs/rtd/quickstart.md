# Quickstart

Follow these steps to get the toolbox running locally.

## Requirements
- Python 3.8+
- PyQt5, numpy, scipy, matplotlib, Dans_Diffraction (listed in `requirements.txt`)

## Install
```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

## Run
```bash
python -m advisor
# or
python main.py
```

## Minimal workflow
1) Launch the app.  
2) Enter lattice constants/angles and beam energy, or drop a CIF file.  
3) Click **Initialize**.  
4) Switch between feature tabs (Brillouin / Structure Factor) to calculate and visualize.

<!-- TODO: Insert a short GIF of launching the app and initializing parameters. -->
