"""Phase 1: all seven YAML configs load, validate and hold the blueprint's key values."""

from datetime import datetime, timezone

from app.config_loader import load_configs


def test_all_configs_load_and_expose_expected_values():
    cfg = load_configs()
    assert cfg.exposure.horizon_hours == 72
    assert cfg.exposure.alert_threshold == 50
    assert cfg.stress.due_buffer_hours == 24
    assert cfg.stress.transport_hours == 4
    assert cfg.matching.recommended_set_size == 2
    assert cfg.readiness.default_window_hours == 48
    assert cfg.readiness.windows == [24, 48, 72]


def test_processes_catalogue_marks_vendor_batch_processes():
    cfg = load_configs()
    assert "TURN" in cfg.processes
    assert cfg.processes["HEAT_TREAT"].water_dependent is True
    assert cfg.processes["HEAT_TREAT"].vendor_batch is True
    assert cfg.processes["TURN"].vendor_batch is False


def test_materials_catalogue_contains_the_demo_materials():
    cfg = load_configs()
    grades = {material.grade for material in cfg.materials}
    assert {"EN8", "EN24", "SS304", "Al6061"} <= grades


def test_cluster_has_one_owner_and_the_story_sites():
    cfg = load_configs()
    owners = [site for site in cfg.cluster.sites if site.role == "OWNER"]
    assert len(owners) == 1
    ids = {site.id for site in cfg.cluster.sites}
    assert {"fac_owner", "ven_heat", "sup_steel", "fac_oragadam", "fac_hosur", "fac_peenya", "fac_cbe"} <= ids


def test_backtest_sites_cover_flooded_and_not_flooded():
    cfg = load_configs()
    assert len(cfg.cluster.backtest_flooded) >= 3
    assert len(cfg.cluster.backtest_not_flooded) >= 3


def test_replay_window_uses_the_phase0_verified_start():
    # docs/VERIFIED_FACTS.md: storm peak 2023-12-04, series starts 2023-12-03T00:00Z.
    replay = load_configs().cluster.replay
    assert replay is not None
    assert replay.series_start_utc == datetime(2023, 12, 3, 0, 0, 0, tzinfo=timezone.utc)
    assert replay.series_hours == 72


def test_load_is_cached():
    assert load_configs() is load_configs()