Quickstart
==========

Requirements
------------
- Python 3.8+
- PyQt5, numpy, scipy, matplotlib, Dans_Diffraction (see ``requirements.txt``)

Install
-------
Pick one of the following:

- From PyPI (recommended)::

    pip install ad-visor


- From GitHub (latest main)::

    git clone https://github.com/HongXunyang/advisor.git
    cd advisor
    python -m venv .venv
    source .venv/bin/activate  # or .venv\Scripts\activate on Windows
    pip install -r requirements.txt
    pip install .

Run
---
::

   ad-visor
   # or
   advisor
   # or
   python -m advisor


Minimal workflow
----------------
1. Launch the app.  
2. Enter lattice constants/angles and beam energy, or drop a CIF file.  
3. Click **Initialize**.  
4. Switch between feature tabs (Brillouin / Structure Factor) to calculate and visualize.

Animation Example
^^^^^^^^^^^^^^^^^

Here is a demonstration of the initialization process:

.. image:: _static/init.gif
   :alt: Algorithm animation
   :width: 100%
   :align: center
