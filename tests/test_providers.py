import json
from datetime import date

import pytest

from helpers import fixed_clock, in_window, make_service, write_fixture
from trading_scanner.config import PACKAGED_FIXTURE_DIR, Settings
from trading_scanner.models import ResultState, ScanRequest
from trading_scanner.providers import (
    FixtureFormatError,
    FixtureProvider,
    NoSessionError,
    ProviderError,
    SymbolResolutionError,
)
from trading_scanner.service import ScanService
from trading_scanner.synthetic import demo_scenarios

PROVIDER = FixtureProvider(PACKAGED_FIXTURE_DIR)


@pytest.mark.parametrize(
    "name, symbol",
    [("HCLTECH", "HCLTECH"), ("hcl technologies", "HCLTECH"), ("  HCL   Technologies ", "HCLTECH"),
     ("Sun Pharma", "SUNPHARMA"), ("asian paints", "ASIANPAINT"), ("L&T", "LT"), ("l & t", "LT"),
     ("Larsen & Toubro", "LT"), ("lt", "LT"), ("syn-long", "SYN-LONG")],
)
def test_fixture_aliases_resolve_to_cash_equity(name, symbol):
    instrument = PROVIDER.resolve(name)
    assert instrument.symbol == symbol and instrument.exchange == "NSE" and instrument.segment == "cash_equity"
    assert instrument.provider_id is None  # no fabricated security identifiers
    assert instrument.synthetic is symbol.startswith("SYN-")


def test_unknown_name_is_a_resolution_error():
    with pytest.raises(SymbolResolutionError, match="not a known instrument"):
        PROVIDER.resolve("LT FUT")


def test_missing_recording_is_reported_not_substituted():
    instrument = PROVIDER.resolve("HCLTECH")
    with pytest.raises(ProviderError, match="nothing was substituted"):
        PROVIDER.fetch_candles(instrument, date(2026, 11, 12))


def base_document(symbol="SYN-A", name="Synthetic A", **overrides):
    document = {
        "fixture_format": 1, "kind": "synthetic", "label": "SYNTHETIC test",
        "instrument": {"symbol": symbol, "name": name, "aliases": []},
        "trading_date": "2026-11-13", "timezone": "Asia/Kolkata", "interval_minutes": 5,
        "as_of": "2026-11-13T15:30:00+05:30", "source": "test", "candles": [],
    }
    document.update(overrides)
    return document


def test_ambiguous_alias_is_reported(tmp_path):
    write_fixture(tmp_path, "a.json", base_document("SYN-A", "Synthetic A", instrument={"symbol": "SYN-A", "name": "A", "aliases": ["Shared"]}))
    write_fixture(tmp_path, "b.json", base_document("SYN-B", "Synthetic B", instrument={"symbol": "SYN-B", "name": "B", "aliases": ["shared"]}))
    with pytest.raises(SymbolResolutionError, match="ambiguous"):
        FixtureProvider(tmp_path).resolve("SHARED")


def test_closed_session_fixture_reports_no_session(tmp_path):
    write_fixture(tmp_path, "closed.json", base_document(session="closed", label="SYNTHETIC closed day"))
    provider = FixtureProvider(tmp_path)
    with pytest.raises(NoSessionError):
        provider.fetch_candles(provider.resolve("SYN-A"), date(2026, 11, 13))
    service = make_service(lambda name: provider)
    result = service.scan(ScanRequest(trading_date="2026-11-13", stocks=["SYN-A"], provider="fixture")).results[0]
    assert result.state is ResultState.NO_SESSION and result.entry is None


@pytest.mark.parametrize(
    "document, message",
    [
        (base_document(symbol="HCLTECH"), "must use a SYN- symbol"),
        (base_document(kind="chart_observation"), "not synthetic"),
        (base_document(candles=[["2026-11-13T09:15:00+05:30", "1", "2"]]), "candle row 0"),
        (base_document(as_of="2026-11-13T15:30:00"), "timezone"),
        (base_document(interval_minutes=1), "interval_minutes"),
    ],
)
def test_malformed_fixtures_fail_loudly_at_load(tmp_path, document, message):
    write_fixture(tmp_path, "bad.json", document)
    with pytest.raises(FixtureFormatError, match=message):
        FixtureProvider(tmp_path)


def test_dhan_not_configured_never_falls_back_to_fixtures():
    service = ScanService(settings=Settings(_env_file=None), clock=fixed_clock)
    response = service.scan(ScanRequest(trading_date="2026-11-13", stocks=["HCLTECH", "SYN-LONG"], provider="dhan"))
    assert response.provider == "dhan" and response.synthetic_data_present is False
    for result in response.results:
        assert result.state is ResultState.PROVIDER_ERROR
        assert result.data is None and result.entry is None and result.instrument is None
        assert "not configured" in result.reason and "No fixture or synthetic data was substituted" in result.reason


def test_committed_synthetic_fixtures_match_the_generator():
    for scenario in demo_scenarios():
        path = PACKAGED_FIXTURE_DIR / "synthetic" / f"{scenario.symbol.lower()}.json"
        assert json.loads(path.read_text()) == scenario.document(), f"regenerate {path.name}"


@pytest.mark.parametrize("scenario", demo_scenarios(), ids=lambda s: s.symbol)
def test_every_synthetic_demo_fixture_produces_its_documented_result(scenario):
    response = make_service().scan(ScanRequest(trading_date="2026-11-13", stocks=[scenario.symbol], provider="fixture"))
    (result,) = [r for r in response.results if r.strategy_window == scenario.window]
    expected = scenario.expected
    assert result.strategy_window == scenario.window
    assert result.state.value == expected["state"]
    assert result.data.synthetic is True and result.instrument.synthetic is True
    if "signal" in expected:
        assert result.breakout.signal.value == expected["signal"]
    if "breakout" in expected:
        assert result.breakout.candle_start.strftime("%H:%M") == expected["breakout"]
    if "entry" in expected:
        assert result.entry.time.strftime("%H:%M") == expected["entry"]
        assert str(result.entry.price) == expected["entry_price"]
    if "expected_entry" in expected:
        assert result.entry.expected_time.strftime("%H:%M") == expected["expected_entry"]
        assert result.entry.price is None
    if "rule_decision" in expected:
        assert result.rule_decision.code.value == expected["rule_decision"]
    if "missing" in expected:
        assert result.data.missing_candles == expected["missing"]
    if "cancelled" in expected:
        assert result.cancellation.candle_start.strftime("%H:%M") == expected["cancelled"]
        assert result.breakout is None and result.entry is None


def test_blank_environment_values_mean_unset(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("DHAN_CLIENT_ID=\nDHAN_ACCESS_TOKEN=\nSCANNER_FIXTURE_DIR=\n")
    settings = Settings(_env_file=env)
    assert settings.resolved_fixture_dir == PACKAGED_FIXTURE_DIR
    assert settings.dhan_configured is False


def test_unquoted_fixture_numbers_are_parsed_without_float_drift(tmp_path):
    from trading_scanner.synthetic import low_qualified

    session = low_qualified().set("11:15", "108.00", "111.50", "107.80", "__CLOSE__").set(
        "11:20", "__OPEN__", "111.90", "110.60", "111.40"
    )
    document = base_document(candles=session.json_rows())
    text = json.dumps(document)
    text = text.replace('"__CLOSE__"', "110.000000000000001").replace('"__OPEN__"', "110.90")
    (tmp_path / "f.json").write_text(text)
    provider = FixtureProvider(tmp_path)
    (result,) = in_window(make_service(lambda name: provider).scan(
        ScanRequest(trading_date="2026-11-13", stocks=["SYN-A"], provider="fixture")
    ).results)
    # As a binary float this close would equal 110.0 and fall on the boundary; as a decimal it is outside.
    assert result.state is ResultState.ENTRY_IDENTIFIED
    assert str(result.breakout.close) == "110.000000000000001" and str(result.entry.price) == "110.90"


def test_project_env_file_is_found_from_any_working_directory():
    from trading_scanner.config import PROJECT_ROOT

    assert PROJECT_ROOT / ".env" in Settings.model_config["env_file"]
