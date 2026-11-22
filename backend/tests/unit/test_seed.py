"""Phase 3: demo world seeding.

Covers the Phase 3 task list: seed loads without FK errors, counts match the
blueprint, dates are RELATIVE to the overridden clock, reset twice gives
identical rows, everything is labelled is_sample=true, and the relationship
setup matches the section 9 story. Invariants that need later modules (M3-M8)
are asserted in their own phases.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config_loader import load_configs
from app.core import clock
from app.db import Base, engine
from app.demo_seed import (
    EXPECTED_COUNTS,
    INITIAL_SNAPSHOT_ID,
    load_seed_data,
    reset_demo,
    seed,
    verify_counts,
)
from app.enums import BackupStatus, CheckKey
from app.models import (
    BackupRelationship,
    Factory,
    Machine,
    Order,
    Part,
    PartStep,
    ReadinessSnapshot,
    RelationshipCheck,
    Vendor,
)


@pytest.fixture(autouse=True)
def _tables():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


# ---------------------------------------------------------------- load + counts


def test_seed_loads_without_fk_errors_and_counts_match():
    with Session(engine) as session:
        counts = seed(session)
        session.commit()  # no IntegrityError -> FK graph is loadable in one pass
        assert counts == EXPECTED_COUNTS
        assert verify_counts(session) == EXPECTED_COUNTS


def test_every_seeded_row_is_sample():
    with Session(engine) as session:
        seed(session)
        session.commit()
        assert all(factory.is_sample for factory in session.scalars(select(Factory)))
        assert all(vendor.is_sample for vendor in session.scalars(select(Vendor)))


def test_seed_is_idempotent_after_wipe():
    """Seeding twice (with a wipe in between) produces the same counts."""
    with Session(engine) as session:
        first = seed(session)
        session.commit()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with Session(engine) as session:
        second = seed(session)
        session.commit()
        assert first == second == EXPECTED_COUNTS


def test_seed_can_run_twice_without_a_wipe():
    """seed() clears its own tables first, so re-running it is safe."""
    with Session(engine) as session:
        seed(session)
        session.commit()
        second = seed(session)
        session.commit()
        assert second == EXPECTED_COUNTS
        assert verify_counts(session) == EXPECTED_COUNTS


# ---------------------------------------------------------------- relative dates


def test_dates_are_relative_to_the_overridden_clock():
    frozen = datetime(2026, 11, 14, 9, 0, 0, tzinfo=timezone.utc)
    with clock.frozen_time(frozen):
        with Session(engine) as session:
            seed(session)
            session.commit()

            due = session.get(Order, "ord_101").due_at
            assert due == frozen + timedelta(days=4)
            # aware-UTC out of the database, exactly at the frozen clock + 4 days
            assert due.tzinfo is not None

            oragadam = session.get(BackupRelationship, "rel_oragadam")
            assert oragadam.last_confirmed_at == frozen - timedelta(days=40)

            peenya = session.get(BackupRelationship, "rel_peenya")
            assert peenya.last_confirmed_at == frozen - timedelta(days=120)

            cbe = session.get(BackupRelationship, "rel_cbe")
            assert cbe.last_confirmed_at is None  # never confirmed

            # check timestamps are stamped at seed time
            done_check = (
                session.scalars(
                    select(RelationshipCheck).where(
                        RelationshipCheck.relationship_id == "rel_oragadam",
                        RelationshipCheck.key == CheckKey.CUSTOMER_APPROVED,
                    )
                ).one()
            )
            assert done_check.done_at == frozen


def test_order_due_dates_cover_the_story_window():
    with Session(engine) as session:
        seed(session)
        session.commit()
        current = clock.now()
        due_days = {o.id: (o.due_at - current).total_seconds() / 86400 for o in session.scalars(select(Order))}
        # two PRT-B orders inside the storm window, one late order outside it
        assert due_days["ord_107"] == pytest.approx(3, abs=1e-6)
        assert due_days["ord_108"] == pytest.approx(12, abs=1e-6)
        soon = [v for k, v in due_days.items() if k != "ord_108" and v <= 5]
        assert len(soon) >= 3  # 101 (4d), 107 (3d), 104 (2d)


# ---------------------------------------------------------------- reset determinism


def _dump_all_tables() -> dict[str, list[tuple]]:
    """Every row of every table, ordered - the fingerprint of a reset."""
    from sqlalchemy import inspect

    inspector = inspect(engine)
    dump: dict[str, list[tuple]] = {}
    with engine.connect() as conn:
        for table in sorted(inspector.get_table_names()):
            rows = conn.exec_driver_sql(f"SELECT * FROM {table}").fetchall()  # noqa: S608 - table names from our own schema
            dump[table] = sorted(map(tuple, rows))
    return dump


def test_reset_twice_gives_identical_rows():
    frozen = datetime(2026, 11, 14, 9, 0, 0, tzinfo=timezone.utc)
    with clock.frozen_time(frozen):
        reset_demo()
        first = _dump_all_tables()
        reset_demo()
        second = _dump_all_tables()
    assert first == second


def test_reset_writes_initial_readiness_snapshot():
    reset_demo()
    with Session(engine) as session:
        snapshot = session.get(ReadinessSnapshot, INITIAL_SNAPSHOT_ID)
        assert snapshot is not None
        assert snapshot.factory_id == "fac_owner"
        assert snapshot.window_hours == 48


# ---------------------------------------------------------------- section 9 story


def test_relationship_story_shape():
    with Session(engine) as session:
        seed(session)
        session.commit()
        rels = {r.partner_id: r for r in session.scalars(select(BackupRelationship))}
        assert set(rels) == {
            "fac_oragadam", "fac_hosur", "fac_peenya", "fac_cbe", "fac_amb_nb", "fac_guindy",
        }

        # Oragadam: READY, fresh (~40 days), every check done
        ora = rels["fac_oragadam"]
        assert ora.status == BackupStatus.READY
        assert all(check.done for check in ora.checks)

        # Hosur: APPROVAL_PENDING, missing exactly CUSTOMER_APPROVED + CAPACITY_RECONFIRMED
        hos = rels["fac_hosur"]
        assert hos.status == BackupStatus.APPROVAL_PENDING
        missing = {check.key for check in hos.checks if not check.done}
        assert missing == {CheckKey.CUSTOMER_APPROVED, CheckKey.CAPACITY_RECONFIRMED}

        # Peenya: READY but stale - confirmed ~120 days ago, past the 90-day window
        pee = rels["fac_peenya"]
        assert pee.status == BackupStatus.READY
        days_since = (clock.now() - pee.last_confirmed_at).total_seconds() / 86400
        assert days_since == pytest.approx(120, abs=1e-6)
        assert days_since > 90

        # Coimbatore: POTENTIAL_MATCH, never confirmed
        assert rels["fac_cbe"].status == BackupStatus.POTENTIAL_MATCH
        assert rels["fac_cbe"].last_confirmed_at is None

        # Ambattur neighbour + Guindy: READY, so exclusion (not status) is the reason
        assert rels["fac_amb_nb"].status == BackupStatus.READY
        assert rels["fac_guindy"].status == BackupStatus.READY
        assert all(check.done for check in rels["fac_amb_nb"].checks)


def test_owner_machine_fleet_matches_section_9():
    with Session(engine) as session:
        seed(session)
        session.commit()
        owner = session.get(Factory, "fac_owner")
        machines = session.scalars(select(Machine).where(Machine.factory_id == owner.id)).all()
        by_process: dict[str, int] = {}
        for machine in machines:
            by_process[machine.process.value] = by_process.get(machine.process.value, 0) + 1
        assert by_process == {"TURN": 3, "MILL": 2, "DRILL_TAP": 1, "GRIND_CYL": 1}
        grinder = next(m for m in machines if m.process.value == "GRIND_CYL")
        assert grinder.achievable_tolerance_mm == pytest.approx(0.005)  # the +-0.005 SPOF


def test_part_routes_match_section_9():
    with Session(engine) as session:
        seed(session)
        session.commit()
        routes = {}
        for part in session.scalars(select(Part)):
            steps = session.scalars(
                select(PartStep).where(PartStep.part_id == part.id).order_by(PartStep.seq)
            ).all()
            routes[part.id] = [step.process.value for step in steps]
        assert routes == {
            "prt_a": ["TURN", "HEAT_TREAT", "GRIND_CYL"],
            "prt_b": ["TURN", "MILL"],
            "prt_c": ["MILL", "DRILL_TAP"],
            "prt_d": ["MILL"],
            "prt_e": ["TURN"],
            "prt_f": ["TURN", "MILL", "HEAT_TREAT"],
        }
        critical = {p.id for p in session.scalars(select(Part)) if p.is_critical}
        assert critical == {"prt_a", "prt_b", "prt_c", "prt_f"}
        grind = (
            session.scalars(
                select(PartStep).where(
                    PartStep.part_id == "prt_a", PartStep.process == "GRIND_CYL"
                )
            ).one()
        )
        assert grind.tolerance_mm == pytest.approx(0.005)
        assert grind.outsourced is False  # in-house step -> grinder is the SPOF
        heat = (
            session.scalars(
                select(PartStep).where(
                    PartStep.part_id == "prt_a", PartStep.process == "HEAT_TREAT"
                )
            ).one()
        )
        assert heat.outsourced is True  # vendor step -> heat vendor is the SPOF


def test_seed_files_consistent_with_cluster_yaml():
    """Seed factories must match the cluster config sites (single story, two views)."""
    bundle = load_configs()
    sites = {site.id: site for site in bundle.cluster.sites}
    data = load_seed_data()
    for row in data["factories"]["factories"]:
        site = sites[row["id"]]
        assert site.role == row["role"]
        assert site.lat == pytest.approx(row["lat"])
        assert site.lon == pytest.approx(row["lon"])
        assert site.cluster_id == row["cluster_id"]
        assert site.hazard_zone_id == row.get("hazard_zone_id")
        assert site.grid_id == row.get("grid_id")
    # and every config site is covered by the seed (factories + vendors files, no drift either way)
    factory_ids = {row["id"] for row in data["factories"]["factories"]}
    vendor_ids = {row["id"] for row in data["vendors"]["vendors"]}
    assert factory_ids | vendor_ids == set(sites)
