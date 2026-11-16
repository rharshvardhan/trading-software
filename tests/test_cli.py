import io
import json

import pytest
from fastapi.testclient import TestClient

from helpers import make_service
from trading_scanner.api import create_app
from trading_scanner.cli import main, split_stocks
from trading_scanner.synthetic import demo_scenarios

ALL_DEMO = [s.symbol for s in demo_scenarios()]


def run(argv, inputs=None):
    out = io.StringIO()
    answers = iter(inputs or [])

    def fake_input(prompt):
        out.write(prompt)
        try:
            return next(answers)
        except StopIteration:
            raise EOFError

    code = main(argv, service=make_service(), input_fn=fake_input, out=out)
    return code, out.getvalue()


def test_split_stocks_accepts_commas_and_multiword_names():
    assert split_stocks(["HCL Technologies, LT", "SUNPHARMA", " ,"]) == ["HCL Technologies", "LT", "SUNPHARMA"]


def test_one_shot_report_lists_every_stock_with_explanations():
    code, text = run(["--provider", "fixture", "--date", "2026-11-13", "--stocks", "SYN-LONG", "SYN-NOTQUAL,NOPE", "HCL Technologies"])
    assert code == 0
    assert "Stock" in text and "Entry open" in text and "Stop loss" in text
    assert "*** SYNTHETIC DATA: SYN-LONG, SYN-NOTQUAL" in text
    assert "₹111.20" in text and "Not defined" in text
    for fragment in ["1. SYN-LONG", "2. SYN-NOTQUAL", "3. NOPE", "4. HCLTECH", "PARTIAL CHART OBSERVATION",
                     "Rules not yet defined", "no orders are placed"]:
        assert fragment in text


def test_details_view_shows_reference_candles_and_evidence():
    _, text = run(["--provider", "fixture", "--date", "2026-11-13", "--stocks", "SYN-DELAYED", "--details"])
    assert "Reference candles:" in text and "10:30  O 105.00  H 110.00  L 104.80  C 109.00" in text
    assert "High side: new_extreme" in text and "Breakout candle: 12:00-12:05" in text


def test_terminal_json_matches_api_json_for_the_same_request():
    stocks = ALL_DEMO + ["HCLTECH", "L&T", "NOPE"]
    _, text = run(["--provider", "fixture", "--date", "2026-11-13", "--stocks", *stocks, "--json"])
    api = TestClient(create_app(make_service())).post(
        "/v1/scans", json={"trading_date": "2026-11-13", "stocks": stocks, "provider": "fixture"}
    )
    assert json.loads(text) == api.json()


def test_interactive_session_validates_input_and_scans_on_enter():
    code, text = run(
        ["--provider", "fixture"],
        ["2026-13-45", "2026-11-20", "2026-11-13", "  ", "SYN-SHORT, SYN-NOTQUAL", "q"],
    )
    assert code == 0
    assert "'2026-13-45' is not a valid date" in text
    assert "Trading date 2026-11-20 is in the future" in text
    assert "Enter at least one stock name or symbol." in text
    assert "SYN-SHORT" in text and "entry_identified" in text and "not_qualified" in text and "₹98.80" in text
    assert text.rstrip().endswith("Goodbye.")


def test_interactive_session_allows_repeated_requests_and_exits_on_eof():
    code, text = run(["--provider", "fixture"], ["2026-11-13", "SYN-LONG", "2026-11-06", "Asian Paints"])
    assert code == 0 and text.count("Explanations") == 2 and "ASIANPAINT" in text and "Goodbye." in text


def test_dhan_provider_reports_unavailability_without_synthetic_banner():
    code, text = run(["--provider", "dhan", "--date", "2026-11-13", "--stocks", "HCLTECH"])
    assert code == 0 and "provider_error" in text and "SYNTHETIC DATA" not in text


def test_list_fixtures_names_kinds():
    code, text = run(["--provider", "fixture", "--list-fixtures"])
    assert code == 0 and "HCLTECH" in text and "chart_observation" in text and "SYN-LONG" in text and "synthetic" in text


def test_one_shot_invalid_request_exits_nonzero_with_message():
    code, text = run(["--provider", "fixture", "--date", "2026-11-31", "--stocks", "SYN-LONG"])
    assert code == 1 and "Invalid request" in text


@pytest.mark.parametrize(
    "argv",
    [["--date", "2026-11-13", "--stocks", "SYN-LONG"], ["--provider", "fixture", "--date", "2026-11-13"],
     ["--provider", "csv"]],
)
def test_argument_errors_exit_with_usage(argv):
    with pytest.raises(SystemExit) as info:
        run(argv)
    assert info.value.code == 2


def test_missing_historical_entry_candle_is_labeled_missing_not_pending():
    from helpers import InMemoryProvider
    from trading_scanner.synthetic import low_qualified

    session = low_qualified().set("11:15", "108.00", "111.50", "107.80", "111.00").drop("11:20")
    provider = InMemoryProvider(sessions={"A15": (session, "15:30", None)})
    out = io.StringIO()
    main(["--provider", "fixture", "--date", "2026-11-13", "--stocks", "A15"],
         service=make_service(lambda name: provider), out=out)
    assert "11:20 missing" in out.getvalue() and "pending" not in out.getvalue()


def test_cli_reports_all_windows_for_every_stock():
    code, text = run(["--provider", "fixture", "--date", "2026-11-13", "--stocks", "SYN-0945-SHORT"])
    assert code == 0 and "windows: 09:45 three-candle + 10:30 four-candle + 10:50 two-candle" in text
    assert "09:45 (3)" in text and "10:30 (4)" in text and "10:50 (2)" in text
    assert "10:30 four-candle window: not_qualified" in text
    assert "09:45 three-candle window: entry_identified" in text and "₹98.80" in text
    _, json_text = run(["--provider", "fixture", "--date", "2026-11-13", "--stocks", "SYN-0945-SHORT", "--json"])
    assert [w["key"] for w in json.loads(json_text)["windows"]] == ["0945_three_candle", "1030_four_candle", "1050_two_candle"]
    with pytest.raises(SystemExit):
        run(["--provider", "fixture", "--window", "0945", "--date", "2026-11-13", "--stocks", "SYN-LONG"])
