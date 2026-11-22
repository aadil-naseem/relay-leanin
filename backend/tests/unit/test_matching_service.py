"""Unit tests for services/matching.py and api/matching.py: hero order story invariant 4, PRT-A fallback level NONE, API search."""

from __future__ import annotations

from app.api import matching as matching_api
from app.db import SessionLocal
from app.demo_seed import reset_demo
from app.enums import BackupStatus, EffectiveStatus, FallbackLevel
from app.schemas.matching import MatchRequest
from app.services import matching as matching_service


def test_hero_order_story_invariant_4():
    """Blueprint Section 9 Invariant 4:

    Matching for the PRT-B hero order returns:
      - exactly one viable READY candidate (Oragadam)
      - exactly one viable APPROVAL_PENDING candidate (Hosur)
      - at least one EXCLUDED for correlated risk (Ambattur neighbour: SAME_HAZARD_ZONE / SAME_CLUSTER).
    """
    reset_demo()
    session = SessionLocal()
    try:
        # ord_102 is PRT-B (Pump shaft, EN8, route TURN -> MILL)
        result = matching_service.find_matches_for_order(session, order_id="ord_102")

        assert result.order_id == "ord_102"
        assert result.fallback_level == FallbackLevel.READY

        # Candidate breakdown
        cand_by_id = {c.partner_id: c for c in result.candidates}

        # 1. Oragadam: viable, READY, non-excluded
        oragadam = cand_by_id["fac_oragadam"]
        assert not oragadam.excluded
        assert oragadam.effective_status == EffectiveStatus.READY
        assert all(f.result in ("PASS", "UNKNOWN") for f in oragadam.filters)

        # 2. Hosur: viable, APPROVAL_PENDING, non-excluded
        hosur = cand_by_id["fac_hosur"]
        assert not hosur.excluded
        assert hosur.status == BackupStatus.APPROVAL_PENDING
        assert hosur.effective_status == EffectiveStatus.APPROVAL_PENDING
        assert all(f.result in ("PASS", "UNKNOWN") for f in hosur.filters)
        # Hosur must show its unverified checks!
        unverified_text = " ".join(hosur.unverified)
        assert "CUSTOMER_APPROVED" in unverified_text
        assert "CAPACITY_RECONFIRMED" in unverified_text

        # 3. Ambattur neighbour: EXCLUDED for correlated risk
        amb_nb = cand_by_id["fac_amb_nb"]
        assert amb_nb.excluded is True
        assert amb_nb.exclusion_reason in ("SAME_HAZARD_ZONE", "SAME_CLUSTER")

        # 4. Verify candidate counts for invariant 4
        viable_ready = [
            c for c in result.candidates
            if not c.excluded and c.effective_status == EffectiveStatus.READY and all(f.result in ("PASS", "UNKNOWN") for f in c.filters)
        ]
        viable_pending = [
            c for c in result.candidates
            if not c.excluded and c.effective_status == EffectiveStatus.APPROVAL_PENDING and all(f.result in ("PASS", "UNKNOWN") for f in c.filters)
        ]
        excluded_correlated = [
            c for c in result.candidates
            if c.excluded and c.exclusion_reason in ("SAME_HAZARD_ZONE", "SAME_CLUSTER", "SAME_GRID", "ALSO_EXPOSED_SAME_EVENT")
        ]

        assert len(viable_ready) == 1
        assert viable_ready[0].partner_id == "fac_oragadam"

        assert len(viable_pending) == 1
        assert viable_pending[0].partner_id == "fac_hosur"

        assert len(excluded_correlated) >= 1
        assert any(c.partner_id == "fac_amb_nb" for c in excluded_correlated)

        # 5. Peenya candidate is READY but STALE
        peenya = cand_by_id["fac_peenya"]
        assert peenya.effective_status == EffectiveStatus.STALE
        assert "RECONFIRM_NEEDED" in peenya.flags
        cap_filter = next(f for f in peenya.filters if f.key == "capacity")
        assert cap_filter.result == "UNKNOWN"

    finally:
        session.close()


def test_prt_a_order_has_no_fallback_invariant_2():
    """Blueprint Section 9 Invariant 2:

    PRT-A Hydraulic piston rod (EN24, TURN -> HEAT_TREAT -> GRIND_CYL +-0.005)
    has no viable partner that can fully cover it -> fallback_level = NONE.
    """
    reset_demo()
    session = SessionLocal()
    try:
        # ord_101 is PRT-A
        result = matching_service.find_matches_for_order(session, order_id="ord_101")

        assert result.order_id == "ord_101"
        assert result.fallback_level == FallbackLevel.NONE
        assert result.best_backup is None

        # Verify why candidates failed or were excluded:
        # - fac_amb_nb has grinding but is EXCLUDED (SAME_HAZARD_ZONE)
        # - fac_cbe has grinder but fails tolerance (0.010 mm cannot hold 0.005 mm)
        # - fac_oragadam lacks GRIND_CYL
        cand_by_id = {c.partner_id: c for c in result.candidates}

        assert cand_by_id["fac_amb_nb"].excluded is True
        cbe_tol = next(f for f in cand_by_id["fac_cbe"].filters if f.key == "tolerance")
        assert cbe_tol.result == "FAIL"

    finally:
        session.close()


def test_api_matching_search_endpoint():
    """Test POST /matching/search router directly."""
    reset_demo()
    session = SessionLocal()
    try:
        req = MatchRequest(order_id="ord_107")
        out = matching_api.search_matching_backups(body=req, db=session)

        assert out.order_id == "ord_107"
        assert out.fallback_level == FallbackLevel.READY
        assert len(out.candidates) > 0
        assert out.recommended_set is not None
        assert "fac_oragadam" in out.recommended_set.partner_ids
        assert len(out.trace) > 0

    finally:
        session.close()
