"""Phase 7: weather adapter and the section 3.4 degradation ladder.

Live is mocked with respx, so these tests never touch the network. Replay and
synthetic read the committed Phase 4 cache.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx
import pytest
import respx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters import weather
from app.core import clock
from app.db import Base, engine
from app.models import ForecastCache

FROZEN = datetime(2026, 11, 14, 9, 0, 0, tzinfo=timezone.utc)
SITES = [
    weather.SiteSpec(site_id="fac_owner", lat=13.100, lon=80.155),
    weather.SiteSpec(site_id="fac_oragadam", lat=12.842, lon=79.952),
]


@pytest.fixture(autouse=True)
def _tables():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def _fake_payload(hours: int = 96, start: datetime = FROZEN) -> list[dict]:
    """Open-Meteo multi-location response shape (array of per-location objects)."""
    # Open-Meteo returns hours from 00:00 UTC of the forecast day
    base = start.replace(hour=0, minute=0, second=0, microsecond=0)
    times = [(base + timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M") for i in range(hours)]
    entries = []
    for index in range(len(SITES)):
        values = [0.0] * hours
        # 5 mm/h from hour 10 onward -> 72 h horizon carries real rain
        for hour in range(10, hours):
            values[hour] = 5.0
        entries.append(
            {
                "latitude": SITES[index].lat,
                "longitude": SITES[index].lon,
                "hourly": {"time": times, "precipitation": values},
            }
        )
    return entries


def test_live_success_slices_from_the_current_hour_and_caches():
    with clock.frozen_time(FROZEN):
        with Session(engine) as session:
            with respx.mock(assert_all_called=True) as mock:
                route = mock.get("https://api.open-meteo.com/v1/forecast").mock(
                    return_value=httpx.Response(200, json=_fake_payload())
                )
                result = weather.get_hourly_precip(session, SITES, "live")

            assert route.called
            request = route.calls[0].request
            assert "latitude=13.1000%2C12.8420" in str(request.url)
            assert "forecast_days=4" in str(request.url)

            assert result.source == "live" and result.degraded is False
            owner = result.series("fac_owner")
            assert len(owner) == 72
            # payload starts at 00:00 and "now" is 09:00 -> first kept hour is 09:00 (dry),
            # hour 1 is 10:00 (first 5 mm hour)
            assert owner[0] == 0.0
            assert owner[1] == pytest.approx(5.0)
            assert sum(owner) == pytest.approx(355.0)

            # every good response is stored for the cache fallback
            keys = {row.key for row in session.scalars(select(ForecastCache))}
            assert len(keys) == 2
            assert all(key.startswith("forecast:") for key in keys)


def test_live_failure_falls_back_to_replay_and_flags_degraded():
    with clock.frozen_time(FROZEN):
        with Session(engine) as session:
            with respx.mock() as mock:
                mock.get("https://api.open-meteo.com/v1/forecast").mock(
                    side_effect=httpx.ConnectError("no network")
                )
                result = weather.get_hourly_precip(session, SITES, "live")

    assert result.source == "replay"
    assert result.degraded is True
    assert len(result.series("fac_owner")) == 72
    assert sum(result.series("fac_owner")) > 200  # the Michaung series, not zeros


def test_live_failure_uses_the_stored_cache_when_present():
    with clock.frozen_time(FROZEN):
        with Session(engine) as session:
            with respx.mock() as mock:
                mock.get("https://api.open-meteo.com/v1/forecast").mock(
                    return_value=httpx.Response(200, json=_fake_payload())
                )
                weather.get_hourly_precip(session, SITES, "live")  # prime the cache

            with respx.mock() as mock:
                mock.get("https://api.open-meteo.com/v1/forecast").mock(
                    side_effect=httpx.ReadTimeout("slow")
                )
                result = weather.get_hourly_precip(session, SITES, "live")

    assert result.source == "cache"
    assert result.degraded is True
    assert sum(result.series("fac_owner")) == pytest.approx(355.0)  # the cached live series


def test_http_error_status_degrades_too():
    with clock.frozen_time(FROZEN):
        with Session(engine) as session:
            with respx.mock() as mock:
                mock.get("https://api.open-meteo.com/v1/forecast").mock(
                    return_value=httpx.Response(503, json={"error": True, "reason": "busy"})
                )
                result = weather.get_hourly_precip(session, SITES, "live")
    assert result.source == "replay" and result.degraded is True


def test_replay_mode_is_not_degraded():
    with clock.frozen_time(FROZEN):
        with Session(engine) as session:
            result = weather.get_hourly_precip(session, SITES, "replay")
    assert result.source == "replay"
    assert result.degraded is False
    assert result.mode == "replay"
    assert result.attribution == "Weather data by Open-Meteo.com"


def test_synthetic_mode_reads_the_labelled_profile():
    with clock.frozen_time(FROZEN):
        with Session(engine) as session:
            result = weather.get_hourly_precip(session, SITES, "synthetic")
    assert result.source == "synthetic"
    assert result.degraded is False
    assert len(result.series("fac_owner")) == 72
    assert max(result.series("fac_owner")) > 0


def test_unknown_mode_is_rejected():
    with Session(engine) as session:
        with pytest.raises(ValueError):
            weather.get_hourly_precip(session, SITES, "rain-dance")


def test_malformed_payload_degrades_instead_of_crashing():
    with clock.frozen_time(FROZEN):
        with Session(engine) as session:
            with respx.mock() as mock:
                # one entry for two sites -> adapter must not guess
                mock.get("https://api.open-meteo.com/v1/forecast").mock(
                    return_value=httpx.Response(200, json=_fake_payload()[:1])
                )
                result = weather.get_hourly_precip(session, SITES, "live")
    assert result.source == "replay" and result.degraded is True