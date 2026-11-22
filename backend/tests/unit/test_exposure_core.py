"""Phase 7: M4 exposure engine pure-function tests (blueprint section 7.2).

Numbers are hand-computed from config/exposure.yaml so a change to the
formulas or the constants fails loudly rather than silently shifting scores.
"""

from __future__ import annotations

import pytest

from app.config_loader import load_configs
from app.core import exposure_score as engine
from app.enums import RiskLevel


@pytest.fixture(scope="module")
def cfg():
    return load_configs().exposure


# ---------------------------------------------------------------- rain -> hazard


def test_rolling_sums_and_max():
    series = [1.0] * 30
    assert engine.rolling_sums(series, 3)[:3] == [3.0, 3.0, 3.0]
    assert len(engine.rolling_sums(series, 3)) == 28
    assert engine.max_rolling(series, 24) == pytest.approx(24.0)
    assert engine.rolling_sums([1.0, 2.0], 5) == []


def test_piecewise_interpolates_and_clamps(cfg):
    breakpoints = cfg.rain_24h_breakpoints_mm
    assert engine.piecewise(0, breakpoints) == 0.0
    assert engine.piecewise(15, breakpoints) == pytest.approx(0.1)
    assert engine.piecewise(64.5, breakpoints) == pytest.approx(0.5)
    # beyond the last breakpoint the hazard is capped at 1.0, not extrapolated
    assert engine.piecewise(500, breakpoints) == 1.0
    # negative input clamps to the first breakpoint
    assert engine.piecewise(-10, breakpoints) == 0.0


def test_148_mm_in_24h_gives_hazard_about_0_86(cfg):
    """Section 3.6 worked example: 148 mm/24 h -> rain hazard 0.86.

    Exact arithmetic from the 24 h breakpoints: between 115.6 mm (0.8) and
    204.5 mm (1.0) -> 0.8 + (148 - 115.6) / (204.5 - 115.6) * 0.2 = 0.8729.
    """
    hazard = engine.piecewise(148.0, cfg.rain_24h_breakpoints_mm)
    assert hazard == pytest.approx(0.873, abs=0.002)
    assert hazard == pytest.approx(0.86, abs=0.02)


def test_rain_hazard_takes_the_worse_of_24h_and_3h(cfg):
    # 148 mm spread evenly over 24 h: peak 3 h = 18.5 mm -> 3h hazard ~0.24, so 24h wins
    spread = [148.0 / 24] * 24
    rain = engine.rain_hazard(spread, cfg)
    assert rain.max24_mm == pytest.approx(148.0, abs=0.1)
    assert rain.peak3_mm == pytest.approx(18.5, abs=0.1)
    assert rain.hazard == pytest.approx(rain.hazard_24)
    assert rain.hazard_24 > rain.hazard_3

    # a cloudburst: 60 mm in 3 h then dry -> the 3 h band dominates
    burst = [0.0] * 21 + [20.0, 20.0, 20.0]
    rain_burst = engine.rain_hazard(burst, cfg)
    assert rain_burst.hazard_3 == pytest.approx(0.85)
    assert rain_burst.hazard == pytest.approx(max(rain_burst.hazard_24, rain_burst.hazard_3))


def test_dry_series_scores_zero(cfg):
    rain = engine.rain_hazard([0.0] * 72, cfg)
    assert rain.hazard == 0.0 and rain.max24_mm == 0.0


# ---------------------------------------------------------------- vulnerability


def test_depression_clamps_at_full_depth(cfg):
    shallow = engine.vulnerability(elevation_m=17.0, ring_mean_m=18.0, nearest_water_m=None, zone_ids=[], cfg=cfg)
    deep = engine.vulnerability(elevation_m=10.0, ring_mean_m=18.0, nearest_water_m=None, zone_ids=[], cfg=cfg)
    # calibration: depression_full_m = 5.0 (a 1 m dip is mild; >= 5 m saturates)
    assert shallow.depression == pytest.approx(0.2)
    assert deep.depression == 1.0  # 8 m below a 5 m full-depth threshold


def test_water_proximity_is_inverse_distance(cfg):
    at_water = engine.vulnerability(elevation_m=10, ring_mean_m=10, nearest_water_m=0.0, zone_ids=[], cfg=cfg)
    far = engine.vulnerability(elevation_m=10, ring_mean_m=10, nearest_water_m=1500.0, zone_ids=[], cfg=cfg)
    unknown = engine.vulnerability(elevation_m=10, ring_mean_m=10, nearest_water_m=None, zone_ids=[], cfg=cfg)
    assert at_water.water_proximity == 1.0
    assert far.water_proximity == 0.0
    assert unknown.water_proximity == 0.0  # unknown is "no evidence", never invented risk


def test_vulnerability_weights_sum_to_the_documented_mix(cfg):
    only_zone = engine.vulnerability(
        elevation_m=10, ring_mean_m=10, nearest_water_m=None, zone_ids=["zone_x"], cfg=cfg
    )
    assert only_zone.value == pytest.approx(cfg.vulnerability_weights["flood_history"])
    full = engine.vulnerability(
        elevation_m=0, ring_mean_m=10, nearest_water_m=0, zone_ids=["zone_x"], cfg=cfg
    )
    assert full.value == pytest.approx(1.0)


def test_site_risk_formula_and_floor(cfg):
    vuln = engine.vulnerability(elevation_m=10, ring_mean_m=10, nearest_water_m=None, zone_ids=[], cfg=cfg)
    # V = 0 -> risk = 100 * H * floor
    assert engine.site_risk(1.0, vuln, cfg) == int(round(100 * cfg.vulnerability_floor))
    assert engine.site_risk(0.0, vuln, cfg) == 0


def test_risk_level_bands():
    assert RiskLevel.from_score(49) == RiskLevel.MODERATE
    assert RiskLevel.from_score(50) == RiskLevel.HIGH
    assert RiskLevel.from_score(75) == RiskLevel.SEVERE


# ---------------------------------------------------------------- routes


def test_route_risk_with_and_without_underpasses(cfg):
    flat_route = engine.RouteFacts(route_id="r1", exit_id="e1", low_share=0.5, underpass_count=0)
    tunnel_route = engine.RouteFacts(route_id="r2", exit_id="e2", low_share=0.5, underpass_count=2)
    risk_flat = engine.route_risk(1.0, flat_route, cfg)
    risk_tunnel = engine.route_risk(1.0, tunnel_route, cfg)
    assert risk_tunnel > risk_flat
    # V_route = 0.6*0.5 + 0.4*min(2,2)/2 = 0.7 -> risk = 100*1*(0.25+0.75*0.7) = 77.5 -> 77/78
    assert risk_tunnel == pytest.approx(77.5, abs=1.0)
    # V_route = 0.6*0.5 + 0 = 0.3 -> 100*(0.25+0.225) = 47.5
    assert risk_flat == pytest.approx(47.5, abs=1.0)


def test_route_without_facts_is_honestly_null(cfg):
    unknown = engine.RouteFacts(route_id="r3", exit_id="e3", low_share=None, underpass_count=None)
    assert engine.route_risk(1.0, unknown, cfg) is None


def test_isolation_requires_every_exit_exposed(cfg):
    at = cfg.alert_threshold
    assert engine.is_isolated([at, at + 10], cfg) is True
    assert engine.is_isolated([at, at - 1], cfg) is False
    assert engine.is_isolated([], cfg) is False
    # a missing route fact cannot prove isolation
    assert engine.is_isolated([at, None], cfg) is False


# ---------------------------------------------------------------- onset + spell


def test_onset_skips_drizzle_and_finds_the_storm(cfg):
    drizzle = [2.0] * 20          # 6 mm/3 h - below the heavy-onset threshold
    storm = [8.0] * 10            # 24 mm/3 h - heavy
    onset, spell = engine.onset_and_wet_spell(drizzle + storm, cfg)
    assert onset == 18  # first 3 h window that reaches the threshold: 2 + 2 + 8 = 12 mm
    assert spell == 10


def test_onset_absent_when_it_never_rains(cfg):
    assert engine.onset_and_wet_spell([0.5] * 72, cfg) == (None, 0)


def test_wet_spell_is_capped(cfg):
    series = [10.0] * 100  # 30 mm/3 h continuously, longer than the cap
    onset, spell = engine.onset_and_wet_spell(series, cfg)
    assert onset == 0
    assert spell == cfg.wet_spell_cap_hours


# ---------------------------------------------------------------- alert


def _exposure(site_id: str, risk: int) -> engine.SiteExposure:
    return engine.SiteExposure(
        site_id=site_id,
        site_role="OWNER",
        site_risk=risk,
        risk_level=RiskLevel.from_score(risk),
        max24_mm=100.0,
        peak3_mm=20.0,
        hazard=0.8,
        vulnerability=0.5,
        onset_in_hours=30,
        wet_spell_hours=12,
    )


def test_alert_threshold_edge_cases(cfg):
    threshold = cfg.alert_threshold
    assert threshold == 50
    below = {"fac_owner": _exposure("fac_owner", 49)}
    at = {"fac_owner": _exposure("fac_owner", 50)}
    above = {"fac_owner": _exposure("fac_owner", 51)}
    assert engine.alert_affected(["fac_owner"], below, threshold) == []
    assert engine.alert_affected(["fac_owner"], at, threshold) == ["fac_owner"]
    assert engine.alert_affected(["fac_owner"], above, threshold) == ["fac_owner"]


def test_alert_watches_the_owner_and_its_vendors_only():
    exposures = {
        "fac_owner": _exposure("fac_owner", 20),
        "ven_heat": _exposure("ven_heat", 60),
        "fac_oragadam": _exposure("fac_oragadam", 90),  # a partner must not raise the owner's alert
    }
    affected = engine.alert_affected(["fac_owner", "ven_heat"], exposures, 50)
    assert affected == ["ven_heat"]


def test_drivers_are_readable_and_honest(cfg):
    rain = engine.RainHazard(
        max24_mm=242.3, peak3_mm=56.0, hazard_24=1.0, hazard_3=0.83, hazard=1.0, max24_window_start=24
    )
    vuln = engine.vulnerability(elevation_m=14.0, ring_mean_m=18.67, nearest_water_m=169.4, zone_ids=["z"], cfg=cfg)
    drivers = engine.explain_drivers(rain=rain, vuln=vuln, role="OWNER", cfg=cfg)
    joined = " | ".join(drivers)
    assert "242 mm" in joined
    assert "cloudburst" in joined
    assert "4.7 m below" in joined
    assert "169 m" in joined
    assert "not an official flood map" in joined  # R9 labelling survives into the UI text