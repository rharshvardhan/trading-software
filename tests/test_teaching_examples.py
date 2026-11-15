"""The user's historical teaching examples (EXAMPLES.md sections 1 to 4).

Only chart-displayed readings are used. The engine's own range, side-comparison,
breakout, and entry steps run on exactly those values. No missing candle is invented,
so a full-session scan of these stocks reports ``invalid_data`` until complete
provider data is available.
"""

from decimal import Decimal

import pytest

from helpers import load_observation, make_service, observed_candles
from trading_scanner.formatting import format_inr
from trading_scanner.models import (
    BreakoutSide,
    ExtremeStatus,
    QualificationDecision,
    ResultState,
    ScanRequest,
    Signal,
)
from trading_scanner.strategy import (
    ReferenceRange,
    classify_close,
    compare_side,
    decide_qualification,
    entry_from_next_candle,
    find_first_breakout,
    reference_range,
)

D = Decimal


def test_hcl_breakout_at_1100_closes_1105_and_enters_at_1105_open():
    fixture = load_observation("hcltech-2026-11-13.json")
    c = observed_candles(fixture)
    rng = reference_range([c["10:30"], c["10:35"], c["10:40"], c["10:45"]])
    assert (rng.low, rng.high) == (D("1390.60"), D("1396.70"))
    assert [s.strftime("%H:%M") for s in rng.high_slots] == ["10:35"]
    assert [s.strftime("%H:%M") for s in rng.low_slots] == ["10:30"]

    assert classify_close(c["10:50"], rng) is None  # closes inside
    assert classify_close(c["10:55"], rng) is None  # closes inside
    breakout = find_first_breakout(rng, [c["10:50"], c["10:55"], c["11:00"], c["11:05"]])
    assert breakout.candle.start.strftime("%H:%M") == "11:00"
    assert breakout.candle.end.strftime("%H:%M") == "11:05" == breakout.confirmed_at.strftime("%H:%M")
    assert breakout.side is BreakoutSide.BELOW and breakout.signal is Signal.SHORT
    assert breakout.candle.close == D("1385.00") and not breakout.entirely_beyond

    entry = entry_from_next_candle(breakout, c["11:05"])
    assert entry.candle.start.strftime("%H:%M") == "11:05"  # not 11:00, not 11:10
    assert entry.price == D("1384.90") and format_inr(entry.price) == "₹1,384.90"
    with pytest.raises(ValueError):
        entry_from_next_candle(breakout, c["10:55"])  # only the immediately following candle may supply entry


def test_sun_pharma_qualifying_setup_breaks_low_and_enters_at_1055_open():
    fixture = load_observation("sunpharma-2026-11-13.json")
    c = observed_candles(fixture)
    observed_range = next(r for r in fixture.partial_readings if r["observation"] == "four-candle range")
    rng = ReferenceRange(high=D(observed_range["high"]), low=D(observed_range["low"]))
    assert (rng.low, rng.high) == (D("1910.00"), D("1915.00"))
    assert c["10:40"].high == rng.high and c["10:40"].low == rng.low  # consistent with the recorded candle

    breakout = find_first_breakout(rng, [c["10:50"], c["10:55"]])
    assert breakout.candle.start.strftime("%H:%M") == "10:50" and breakout.signal is Signal.SHORT
    entry = entry_from_next_candle(breakout, c["10:55"])
    assert entry.price == D("1906.60") and entry.candle.start.strftime("%H:%M") == "10:55"
    assert fixture.user_label.startswith("success example")


@pytest.mark.parametrize("candidate_low", ["2500.90", "2500.60"])  # inspected low vs drawn line
def test_asian_paints_entry_holds_under_both_candidate_lows(candidate_low):
    fixture = load_observation("asianpaint-2026-11-06.json")
    c = observed_candles(fixture)
    rng = ReferenceRange(high=c["10:30"].high, low=D(candidate_low))
    assert rng.high == D("2514.00")
    breakout = find_first_breakout(rng, [c["10:50"], c["10:55"]])
    assert breakout.candle.start.strftime("%H:%M") == "10:50" and breakout.signal is Signal.SHORT
    assert not breakout.entirely_beyond  # 10:50 high 2501.10 traded back through the level (D05)
    entry = entry_from_next_candle(breakout, c["10:55"])
    assert entry.price == D("2495.70")


def test_asian_paints_failure_label_is_kept_as_a_label_not_an_outcome():
    fixture = load_observation("asianpaint-2026-11-06.json")
    assert "failure example" in fixture.user_label
    result = make_service().scan(
        ScanRequest(trading_date="2026-11-06", stocks=["Asian Paints"], provider="fixture")
    ).results[0]
    assert result.state is not ResultState.NOT_QUALIFIED  # never relabeled as a setup failure
    assert result.risk.outcome is None and result.risk.profit_loss is None and result.risk.stop_loss is None
    assert result.data.provenance["user_label"] == fixture.user_label


def test_lt_fails_initial_session_extreme_qualification():
    fixture = load_observation("lt-2026-11-13.json")
    readings = {r["candle"]: r for r in fixture.partial_readings}
    reference_high = max(D(readings[s]["high"]) for s in ("10:30", "10:35", "10:40", "10:45"))
    reference_low = min(D(readings[s]["low"]) for s in ("10:30", "10:35", "10:40", "10:45"))
    assert (reference_low, reference_high) == (D("4162.60"), D("4184.70"))
    high = compare_side(reference_high, D(readings["09:50"]["high"]), "high")
    low = compare_side(reference_low, D(readings["09:20"]["low"]), "low")
    assert high is ExtremeStatus.NOT_EXTREME and low is ExtremeStatus.NOT_EXTREME
    assert decide_qualification(high, low) is QualificationDecision.NOT_QUALIFIED


@pytest.mark.parametrize(
    "stock, day, candle_count",
    [("HCL Technologies", "2026-11-13", 8), ("Sun Pharma", "2026-11-13", 4),
     ("Asian Paints", "2026-11-06", 4), ("L&T", "2026-11-13", 0)],
)
def test_full_scan_of_partial_observations_reports_missing_data_without_fabrication(stock, day, candle_count):
    result = make_service().scan(ScanRequest(trading_date=day, stocks=[stock], provider="fixture")).results[0]
    assert result.state is ResultState.INVALID_DATA
    assert result.data.synthetic is False and result.data.data_label.startswith("PARTIAL CHART OBSERVATION")
    assert result.data.candles_received == candle_count  # exactly the recorded rows, nothing added
    assert "09:15" in result.data.missing_candles and "No candles were filled in" in result.reason
    assert result.entry is None and result.risk.stop_loss is None


def test_observation_files_hold_only_values_recorded_in_examples():
    import re
    from pathlib import Path

    examples = (Path(__file__).resolve().parents[1] / "docs" / "EXAMPLES.md").read_text()
    recorded = {m.replace(",", "") for m in re.findall(r"\d{1,3}(?:,\d{3})*\.\d{2}", examples)}
    for name in ("hcltech-2026-11-13.json", "sunpharma-2026-11-13.json", "asianpaint-2026-11-06.json", "lt-2026-11-13.json"):
        fixture = load_observation(name)
        values = {str(v) for row in fixture.candles for v in row[1:5]}
        values |= {v for r in fixture.partial_readings for k, v in r.items() if k in ("high", "low", "value")}
        assert values <= recorded, (name, values - recorded)
