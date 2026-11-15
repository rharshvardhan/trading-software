import pytest

from helpers import FIXED_NOW, InMemoryProvider, make_service
from trading_scanner.models import ResultState, ScanRequest
from trading_scanner.providers import ProviderError
from trading_scanner.service import InputError, unique_names
from trading_scanner.synthetic import SyntheticSession


def scan(stocks, day="2026-11-13", provider="fixture", service=None):
    service = service or make_service()
    return service.scan(ScanRequest(trading_date=day, stocks=stocks, provider=provider))


def test_a23_batch_keeps_every_stock_with_distinct_reasons_in_input_order():
    response = scan(["SYN-LONG", "SYN-NOTQUAL", "UNKNOWNCO"])
    states = [r.state for r in response.results]
    assert states == [ResultState.ENTRY_IDENTIFIED, ResultState.NOT_QUALIFIED, ResultState.SYMBOL_ERROR]
    assert [r.input_name for r in response.results] == ["SYN-LONG", "SYN-NOTQUAL", "UNKNOWNCO"]
    assert len({r.reason for r in response.results}) == 3


def test_duplicates_and_aliases_of_one_instrument_are_reported_once():
    response = scan(["LT", "lt", " l&t ", "Larsen & Toubro", "SYN-LONG"])
    assert [r.instrument.symbol for r in response.results] == ["LT", "SYN-LONG"]
    assert response.results[0].input_names == ["LT", "l&t", "Larsen & Toubro"]
    assert sum("reported once" in note for note in response.results[0].notes) == 2


def test_unique_names_trims_and_preserves_order():
    assert unique_names([" HCLTECH ", "hcltech", "Sun  Pharma", "sun pharma", "LT"]) == ["HCLTECH", "Sun Pharma", "LT"]


def test_future_trading_date_is_rejected_but_today_is_allowed():
    with pytest.raises(InputError, match="in the future"):
        scan(["SYN-LONG"], day="2026-11-16")
    today = scan(["SYN-LONG"], day=FIXED_NOW.date().isoformat())
    assert today.results[0].state is ResultState.PROVIDER_ERROR  # no recording for that date; nothing substituted


def test_one_provider_failure_does_not_erase_other_results():
    provider = InMemoryProvider(
        sessions={"GOOD": (SyntheticSession(), "15:30", None)},
        errors={"BAD": ProviderError("Upstream timeout; retry later.")},
    )
    response = scan(["BAD", "GOOD"], service=make_service(lambda name: provider))
    assert [r.state for r in response.results] == [ResultState.PROVIDER_ERROR, ResultState.NO_BREAKOUT]
    assert response.results[0].reason == "Upstream timeout; retry later."


def test_contradictory_provider_data_is_invalid_data():
    session = SyntheticSession().set("10:35", "109.00", "108.00", "103.00", "103.50")  # high below open
    provider = InMemoryProvider(sessions={"BADOHLC": (session, "15:30", None)})
    result = scan(["BADOHLC"], service=make_service(lambda name: provider)).results[0]
    assert result.state is ResultState.INVALID_DATA and "Candle at 10:35 is invalid" in result.reason
    assert result.data.candles_in_session == 0 and result.qualification is None


def test_a16_risk_and_exit_fields_stay_null_with_reason():
    result = scan(["SYN-LONG"]).results[0]
    assert result.state is ResultState.ENTRY_IDENTIFIED
    risk = result.risk.model_dump()
    assert risk.pop("reason") == "Rules not yet defined"
    assert all(value is None for value in risk.values())


def test_result_carries_identity_and_provenance():
    response = scan(["SYN-LONG"])
    result = response.results[0]
    assert (result.timezone, result.interval, result.strategy_version) == ("Asia/Kolkata", "5m", "0.2.0")
    assert result.data.provider == "fixture" and result.data.source == "fixture:synthetic/syn-long.json"
    assert result.data.session_complete is True and result.data.last_closed_candle == "15:25"
    assert result.data.retrieved_at == FIXED_NOW and response.scanned_at == FIXED_NOW
    assert response.synthetic_data_present is True
    assert scan(["HCLTECH"]).synthetic_data_present is False


def test_same_request_gives_identical_output():
    assert scan(["SYN-DELAYED", "SYN-TIE"]).model_dump() == scan(["SYN-DELAYED", "SYN-TIE"]).model_dump()


class _CorruptingProvider(InMemoryProvider):
    """Replaces one synthetic candle with a malformed row to simulate a bad provider value."""

    def __init__(self, sessions, corrupt):
        super().__init__(sessions=sessions)
        self.corrupt = corrupt

    def fetch_candles(self, instrument, trading_date):
        response = super().fetch_candles(instrument, trading_date)
        if instrument.symbol not in self.corrupt:
            return response
        from dataclasses import replace

        rows = list(response.candles)
        rows[-1] = self.corrupt[instrument.symbol](rows[-1])
        return replace(response, candles=tuple(rows))


@pytest.mark.parametrize(
    "corruption",
    [lambda row: row.__class__(row.start, row.open, row.high, row.low, row.close, "abc"),
     lambda row: row.__class__(10**20, row.open, row.high, row.low, row.close, row.volume)],
    ids=["unparseable-volume", "overflowing-epoch"],
)
def test_one_malformed_value_does_not_crash_the_batch(corruption):
    provider = _CorruptingProvider(
        sessions={"GOOD": (SyntheticSession(), "15:30", None), "BAD": (SyntheticSession(), "15:30", None)},
        corrupt={"BAD": corruption},
    )
    response = scan(["GOOD", "BAD"], service=make_service(lambda name: provider))
    assert [r.state for r in response.results] == [ResultState.NO_BREAKOUT, ResultState.INVALID_DATA]


def test_every_result_names_its_provider_and_synthetic_flag():
    fixture = scan(["SYN-LONG", "HCLTECH", "NOPE"])
    assert [(r.provider, r.synthetic) for r in fixture.results] == [("fixture", True), ("fixture", False), ("fixture", False)]
    from trading_scanner.config import Settings
    from trading_scanner.service import ScanService
    from helpers import fixed_clock

    dhan = ScanService(settings=Settings(_env_file=None), clock=fixed_clock).scan(
        ScanRequest(trading_date="2026-11-13", stocks=["SYN-LONG"], provider="dhan")
    )
    assert [(r.provider, r.synthetic, r.state) for r in dhan.results] == [("dhan", False, ResultState.PROVIDER_ERROR)]
