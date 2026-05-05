"""Tests for BSE bulk deals scraper — parser unit tests."""

from app.db.models import DealSide
from app.services.scrapers import parse_csv_deals, parse_html_deals

SAMPLE_CSV = """Deal Date,Security Code,Security Name,Client Name,Deal Type,Quantity,Price,Remarks
05-05-2026,500325,Reliance Industries Ltd,RARE ENTERPRISES,B,50000,2450.50,
05-05-2026,532540,TCS Ltd,MORGAN STANLEY INDIA,S,25000,3800.75,
04-05-2026,500180,HDFC Bank Ltd,GOLDMAN SACHS,B,100000,1650.00,
"""


def test_parse_csv_deals_success():
    deals = parse_csv_deals(SAMPLE_CSV)
    assert len(deals) == 3

    assert deals[0]["symbol"] == "500325"
    assert deals[0]["name"] == "Reliance Industries Ltd"
    assert deals[0]["party_name"] == "RARE ENTERPRISES"
    assert deals[0]["side"] == DealSide.BUY
    assert deals[0]["qty"] == 50000
    assert deals[0]["avg_price"] == 2450.50

    assert deals[1]["side"] == DealSide.SELL
    assert deals[1]["qty"] == 25000

    assert deals[2]["party_name"] == "GOLDMAN SACHS"


def test_parse_csv_deals_empty():
    deals = parse_csv_deals("")
    assert deals == []


def test_parse_csv_deals_header_only():
    deals = parse_csv_deals("Deal Date,Security Code,Security Name,Client Name,Deal Type,Quantity,Price\n")
    assert deals == []


def test_parse_csv_deals_malformed_rows():
    csv = "Header\nbad,row\nalso,bad\n"
    deals = parse_csv_deals(csv)
    assert deals == []


SAMPLE_HTML = """
<html><body>
<table id="ContentPlaceHolder1_gvbulk">
<tr><th>Deal Date</th><th>Security Code</th><th>Security Name</th><th>Client Name</th><th>Deal Type</th><th>Quantity</th><th>Price</th></tr>
<tr><td>05-05-2026</td><td>500325</td><td>Reliance</td><td>RARE ENTERPRISES</td><td>B</td><td>50,000</td><td>2,450.50</td></tr>
<tr><td>05-05-2026</td><td>532540</td><td>TCS</td><td>CITADEL</td><td>S</td><td>10,000</td><td>3,800.00</td></tr>
</table>
</body></html>
"""


def test_parse_html_deals_success():
    deals = parse_html_deals(SAMPLE_HTML)
    assert len(deals) == 2
    assert deals[0]["party_name"] == "RARE ENTERPRISES"
    assert deals[0]["side"] == DealSide.BUY
    assert deals[0]["qty"] == 50000
    assert deals[0]["avg_price"] == 2450.50
    assert deals[1]["side"] == DealSide.SELL


def test_parse_html_deals_no_table():
    deals = parse_html_deals("<html><body><p>No data</p></body></html>")
    assert deals == []
