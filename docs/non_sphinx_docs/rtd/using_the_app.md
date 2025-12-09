# Using the App

This section walks through the main windows and tabs so you know where to click and what to expect.

## Initialization window
- Enter lattice constants (a, b, c) and angles (α, β, γ).
- Enter beam energy (eV); wavelength and |k| update automatically.
- Optional: drop a CIF file to auto-fill lattice parameters and show a unit cell preview.
- Euler angles (roll, pitch, yaw) update the coordinate visualizer live.
- Click **Initialize** to pass parameters to all tabs and open the main interface.

<!-- TODO: Add a screenshot of the init window with callouts. -->

## Main interface
- Tabs on the left (vertical) hold each feature.  
- Status bar shows simple feedback; toolbar has a reset shortcut to return to init.

### Scattering Geometry tab
- Convert angles ↔ HKL, scan HKL trajectories, and view scattering geometry.
- Subtabs include:
  - **Angles → HKL**: enter tth/θ/φ/χ, compute H,K,L, and see the geometry + unit cell.
  - **HKL → Angles**: enter H,K,L, get feasible angles (feasible rows highlighted).
  - **HK scan**: explore fixed-tth trajectories with the 3D visualizer.
- HKL results table uses soft colors to flag feasible vs infeasible solutions.

<!-- TODO: Insert a 3–5s clip showing angles→HKL calculation and the plot update. -->

### Structure Factor tab
- Requires a CIF (from the init window) and an energy input in the tab.
- Two subtabs:
  - **HKL plane**: initialize, then view a 3D HKL cube with translucent planes and synced 2D slices (HK/HL/KL). Plane sliders update both 2D/3D views.
  - **Customized plane**: pick arbitrary plane values and visualize structure factors on that slice.
- Initialization status shows green/red messages; missing CIF prompts a warning.

<!-- TODO: Add a still image of the 3D HKL cube with highlighted planes. -->

## Resetting
- Use the toolbar button or **File → Reset Parameters** to go back to the init window, clear the CIF lock, and re-enter parameters.
