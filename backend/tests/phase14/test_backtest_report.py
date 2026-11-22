"""Run the committed replay back-test without rewriting the checked-in report."""

from __future__ import annotations

from scripts import backtest_exposure


def test_michaung_backtest_report_passes_with_positive_separation(phase14_client, tmp_path, monkeypatch):
    monkeypatch.setattr(backtest_exposure, "DOCS_DIR", tmp_path)
    assert backtest_exposure.main() == 0

    report = (tmp_path / "BACKTEST_EXPOSURE.md").read_text(encoding="utf-8")
    assert "Separation (lowest flooded - highest not-flooded): **+22 points**." in report
    assert "Result: **PASS**" in report
    assert "risk indicator, not a flood model" in report
