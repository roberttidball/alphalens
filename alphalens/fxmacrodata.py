"""FXMacroData event helpers for Alphalens factor studies."""

from __future__ import absolute_import

import json
import os

import pandas as pd

try:
    from urllib.parse import urlencode
    from urllib.request import urlopen
except ImportError:  # pragma: no cover - Python 2 compatibility
    from urllib import urlencode
    from urllib2 import urlopen

FXMACRODATA_BASE_URL = "https://fxmacrodata.com/api/v1"


def get_fxmacrodata_calendar(
    currency="usd",
    limit=100,
    min_tier=None,
    api_key=None,
    base_url=FXMACRODATA_BASE_URL,
):
    """Fetch FXMacroData macro release events as a pandas DataFrame."""
    limit = max(1, int(limit))
    params = {"limit": limit}
    token = api_key or os.environ.get("FXMACRODATA_API_KEY")
    if token:
        params["api_key"] = token

    url = "%s/calendar/%s?%s" % (
        base_url.rstrip("/"),
        currency.lower(),
        urlencode(params),
    )
    response = urlopen(url, timeout=30)  # nosec B310
    try:
        payload = json.loads(response.read().decode("utf-8"))
    finally:
        response.close()

    events = payload.get("data", [])
    if min_tier is not None:
        events = [
            event
            for event in events
            if int(event.get("market_tier") or 99) <= int(min_tier)
        ]

    frame = pd.DataFrame(events[:limit])
    if frame.empty:
        return frame
    if "date" in frame.columns:
        frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
        frame = frame.set_index("date").sort_index()
    if "announcement_datetime" in frame.columns:
        frame["announcement_datetime"] = pd.to_datetime(
            frame["announcement_datetime"], unit="s", utc=True, errors="coerce"
        )
    return frame


def event_window_mask(factor_index, events, days_before=1, days_after=1):
    """Return a boolean mask for factor dates near macro release events."""
    dates = pd.DatetimeIndex(factor_index)
    normalized = dates.normalize()
    mask = pd.Series(False, index=factor_index)
    if events.empty:
        return mask

    for event_date in pd.DatetimeIndex(events.index).dropna().normalize():
        start = event_date - pd.Timedelta(days=days_before)
        end = event_date + pd.Timedelta(days=days_after)
        mask |= (normalized >= start) & (normalized <= end)
    return mask
