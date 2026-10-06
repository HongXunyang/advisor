# ADVISOR vs BLISS UB validation

36 two-reflection orientation cases from ESRF ID20 (`bliss_ub_test.csv`, `;`-separated):
inputs, ADVISOR's UB (`UB_ij`, from ADVISOR's Kabsch method) and BLISS's UB (`uij`).

- `python3 -m pytest tests/bliss_validation` checks the frame convention
  (`UB_BLISS = P @ UB_ADVISOR`, `P = [[0,1,0],[-1,0,0],[0,0,1]]`), Busing–Levy agreement with BLISS
  (≤ 1e-6 Å⁻¹) and Kabsch closeness (≤ 1°, bounded by each row's reflection-angle mismatch).
- `python3 tests/bliss_validation/generate_bliss_comparison_report.py` rebuilds
  `bliss_ub_comparison_report.html` by running the same checks. It exits 1 if any check fails.

The BLISS values are kept exactly as supplied. They have 5–9 decimals, mostly 8.
