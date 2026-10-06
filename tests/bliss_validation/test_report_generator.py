"""The HTML report's verdict must follow the actual checks, never a fixed label."""
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("bliss_report", HERE / "generate_bliss_comparison_report.py")
report = importlib.util.module_from_spec(spec)
spec.loader.exec_module(report)
cmp = report.cmp


def test_unchanged_reference_reports_all_checks_passing():
    outcomes = cmp.run_all_checks(cmp.HEADER, cmp.RAW_ROWS, cmp.CASES)
    page = report.build(report.analyse(), outcomes)
    assert all(msg is None for _, _, msg in outcomes)
    assert f"{len(outcomes)} / {len(outcomes)} pass" in page
    assert "Validation FAILED" not in page


def test_reference_beyond_tolerance_is_reported_as_failure():
    perturbed = [dict(c, ub_bliss=c["ub_bliss"].copy()) for c in cmp.CASES]
    perturbed[0]["ub_bliss"][0, 0] += 0.002
    outcomes = cmp.run_all_checks(cmp.HEADER, cmp.RAW_ROWS, perturbed)
    page = report.build(report.analyse(), outcomes)
    n_failed = sum(msg is not None for _, _, msg in outcomes)
    assert n_failed >= 1
    assert f"Validation FAILED: {n_failed} of {len(outcomes)} checks" in page
    assert f"{len(outcomes)} / {len(outcomes)} pass" not in page
    assert "all passing in this run" not in page
