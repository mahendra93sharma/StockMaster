"""Tests for NSE block deals and news/corporate actions parsers."""

from app.db.models import CorporateActionType, DealSide
from app.services.scrapers.corporate_actions import _map_action_type, parse_corporate_actions
from app.services.scrapers.news import parse_bse_announcements
from app.services.scrapers.nse_block_deals import parse_nse_block_deals

# ─── NSE Block Deals ─────────────────────────────────────────────────────────


def test_parse_nse_block_deals_success():
    data = [
        {
            "BD_DT_DATE": "05-May-2026",
            "BD_SYMBOL": "RELIANCE",
            "BD_SCRIP_NAME": "Reliance Industries Limited",
            "BD_CLIENT_NAME": "MORGAN STANLEY INDIA",
            "BD_BUY_SELL": "Buy",
            "BD_QTY_TRD": "500000",
            "BD_TP_WATP": "2450.50",
        },
        {
            "BD_DT_DATE": "05-May-2026",
            "BD_SYMBOL": "TCS",
            "BD_SCRIP_NAME": "Tata Consultancy Services",
            "BD_CLIENT_NAME": "GOLDMAN SACHS",
            "BD_BUY_SELL": "Sell",
            "BD_QTY_TRD": "200,000",
            "BD_TP_WATP": "3,800.75",
        },
    ]
    deals = parse_nse_block_deals(data)
    assert len(deals) == 2
    assert deals[0]["symbol"] == "RELIANCE"
    assert deals[0]["party_name"] == "MORGAN STANLEY INDIA"
    assert deals[0]["side"] == DealSide.BUY
    assert deals[0]["qty"] == 500000
    assert deals[0]["avg_price"] == 2450.50
    assert deals[1]["side"] == DealSide.SELL
    assert deals[1]["qty"] == 200000


def test_parse_nse_block_deals_empty():
    assert parse_nse_block_deals([]) == []


def test_parse_nse_block_deals_malformed():
    data = [{"BD_SYMBOL": "TEST"}]  # Missing required fields
    deals = parse_nse_block_deals(data)
    # Should still parse (with defaults) or skip gracefully
    assert isinstance(deals, list)


# ─── BSE News ────────────────────────────────────────────────────────────────


def test_parse_bse_announcements_success():
    data = [
        {
            "SCRIP_CD": "500325",
            "SLONGNAME": "Reliance Industries",
            "NEWSSUB": "Board Meeting Outcome - Quarterly Results",
            "DT_TM": "2026-05-05T14:30:00",
            "ATTACHMENTNAME": "result_500325.pdf",
            "CATEGORYNAME": "Result",
        },
        {
            "SCRIP_CD": "532540",
            "SLONGNAME": "TCS",
            "NEWSSUB": "Announcement under Regulation 30",
            "DT_TM": "2026-05-04T10:00:00",
            "ATTACHMENTNAME": "",
            "CATEGORYNAME": "General",
        },
    ]
    news = parse_bse_announcements(data)
    assert len(news) == 2
    assert news[0]["symbol"] == "500325"
    assert "Board Meeting" in news[0]["title"]
    assert news[0]["source"] == "BSE/Result"
    assert "result_500325.pdf" in news[0]["url"]
    assert news[1]["source"] == "BSE/General"


def test_parse_bse_announcements_empty():
    assert parse_bse_announcements([]) == []


def test_parse_bse_announcements_skips_empty_title():
    data = [{"SCRIP_CD": "500325", "NEWSSUB": "", "DT_TM": "2026-05-05T10:00:00"}]
    news = parse_bse_announcements(data)
    assert news == []


# ─── Corporate Actions ───────────────────────────────────────────────────────


def test_map_action_type():
    assert _map_action_type("Interim Dividend - Rs 10") == CorporateActionType.dividend
    assert _map_action_type("Stock Split/Sub-Division") == CorporateActionType.split
    assert _map_action_type("Bonus issue 1:2") == CorporateActionType.bonus
    assert _map_action_type("Scheme of Merger") == CorporateActionType.merger
    assert _map_action_type("Demerger of business") == CorporateActionType.demerger
    assert _map_action_type("AGM") is None


def test_parse_corporate_actions_success():
    data = [
        {
            "scrip_code": "500325",
            "long_name": "Reliance Industries",
            "purpose": "Final Dividend - Rs 8 Per Share",
            "ex_dt": "15/05/2026",
        },
        {
            "scrip_code": "532540",
            "long_name": "TCS",
            "purpose": "Bonus Issue 1:1",
            "ex_dt": "20/05/2026",
        },
        {
            "scrip_code": "500180",
            "long_name": "HDFC Bank",
            "purpose": "AGM Notice",  # Should be skipped (unknown type)
            "ex_dt": "01/06/2026",
        },
    ]
    actions = parse_corporate_actions(data)
    assert len(actions) == 2  # AGM is skipped
    assert actions[0]["type"] == CorporateActionType.dividend
    assert actions[0]["symbol"] == "500325"
    assert actions[1]["type"] == CorporateActionType.bonus


def test_parse_corporate_actions_empty():
    assert parse_corporate_actions([]) == []
