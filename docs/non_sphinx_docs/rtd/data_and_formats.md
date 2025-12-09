# Data & Formats

## Inputs
- **Lattice parameters:** a, b, c (Å) and α, β, γ (°).
- **Beam energy:** eV (wavelength and |k| are derived).
- **CIF file (optional but recommended):** drop in the init window to auto-fill lattice and enable structure factor calculations.

## CIF handling
- The init window parses `_cell_length_*` and `_cell_angle_*` from the CIF.
- After a CIF is accepted, lattice inputs lock for the session; reset to change CIF.
- The Structure Factor tab reuses the same CIF; it warns if none is provided.

## Results (conceptual)
- Brillouin tab: HKL values, scattering angles, feasibility flags, and plots (geometry, HKL scans).
- Structure Factor tab: |F| values on HKL grids/planes in 3D and 2D.

<!-- TODO: Provide a sample CIF download link and a small animated GIF of dropping it in. -->

## Sample data
- A sample CIF is available at `resources/data/nacl.cif`.

## Potential exports
- Current UI focuses on visualization; saving plots/results can be added.  
  <!-- TODO: Document export steps once implemented (images/CSV). -->

