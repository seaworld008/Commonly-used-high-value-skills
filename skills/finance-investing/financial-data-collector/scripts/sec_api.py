#!/usr/bin/env python3

import argparse
import gzip
import json
import ssl
from pathlib import Path
from urllib.request import Request, urlopen


SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
SEC_COMPANYFACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
DEFAULT_USER_AGENT = "CodexFinanceSkills/1.0 finance-research@example.com"

US_GAAP_CONCEPTS = {
    "revenue": ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet"],
    "ebit": ["OperatingIncomeLoss"],
    "net_income": ["NetIncomeLoss"],
    "operating_cash_flow": ["NetCashProvidedByUsedInOperatingActivities"],
    "capex": ["PaymentsToAcquirePropertyPlantAndEquipment"],
    "depreciation_amortization": ["DepreciationDepletionAndAmortization"],
    "cash_and_equivalents": ["CashAndCashEquivalentsAtCarryingValue"],
    "total_assets": ["Assets"],
    "current_assets": ["AssetsCurrent"],
    "current_liabilities": ["LiabilitiesCurrent"],
    "total_equity": ["StockholdersEquity"],
    "shares_outstanding": ["CommonStockSharesOutstanding"],
}

ANNUAL_FORMS = {"10-K", "20-F", "40-F", "10-K/A", "20-F/A", "40-F/A"}


def zero_pad_cik(cik: int | str) -> str:
    return str(cik).zfill(10)


def fetch_json(url: str, user_agent: str = DEFAULT_USER_AGENT) -> dict:
    request = Request(
        url,
        headers={
            "User-Agent": user_agent,
            "Accept-Encoding": "gzip, deflate",
            "Host": "www.sec.gov" if "sec.gov/files/" in url else "data.sec.gov",
        },
    )
    context = ssl.create_default_context()
    with urlopen(request, context=context, timeout=30) as response:
        payload = response.read()
        if response.headers.get("Content-Encoding") == "gzip":
            payload = gzip.decompress(payload)
        return json.loads(payload.decode("utf-8"))


def load_json_input(path_or_url: str, user_agent: str = DEFAULT_USER_AGENT) -> dict:
    if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
        return fetch_json(path_or_url, user_agent=user_agent)
    return json.loads(Path(path_or_url).read_text(encoding="utf-8"))


def resolve_ticker_to_cik(ticker: str, tickers_payload: dict) -> str | None:
    target = ticker.upper()
    for record in tickers_payload.values():
        if record.get("ticker", "").upper() == target:
            return zero_pad_cik(record["cik_str"])
    return None


def latest_fact_value(
    companyfacts: dict,
    concept_names: list[str],
    unit: str = "USD",
    annual_only: bool = False,
) -> float | None:
    us_gaap = companyfacts.get("facts", {}).get("us-gaap", {})
    candidates = []
    for concept_name in concept_names:
        concept = us_gaap.get(concept_name)
        if not concept:
            continue
        unit_items = concept.get("units", {}).get(unit, [])
        if not unit_items:
            continue
        if annual_only:
            annual_items = [
                item
                for item in unit_items
                if item.get("form") in ANNUAL_FORMS or item.get("fp") == "FY"
            ]
            if annual_items:
                unit_items = annual_items
        candidates.extend(unit_items)

    if not candidates:
        return None

    latest = sorted(
        candidates,
        key=lambda item: ((item.get("fy") or 0), item.get("end") or "", item.get("filed") or ""),
        reverse=True,
    )[0]
    value = latest.get("val")
    if value is None:
        return None
    return float(value) / 1_000_000


def parse_companyfacts(companyfacts: dict) -> dict:
    shares = latest_fact_value(companyfacts, US_GAAP_CONCEPTS["shares_outstanding"], unit="shares")
    current_assets = latest_fact_value(companyfacts, US_GAAP_CONCEPTS["current_assets"])
    current_liabilities = latest_fact_value(companyfacts, US_GAAP_CONCEPTS["current_liabilities"])

    return {
        "company_name": companyfacts.get("entityName"),
        "latest_facts": {
            "revenue_millions": latest_fact_value(
                companyfacts, US_GAAP_CONCEPTS["revenue"], annual_only=True
            ),
            "ebit_millions": latest_fact_value(
                companyfacts, US_GAAP_CONCEPTS["ebit"], annual_only=True
            ),
            "net_income_millions": latest_fact_value(
                companyfacts, US_GAAP_CONCEPTS["net_income"], annual_only=True
            ),
            "operating_cash_flow_millions": latest_fact_value(
                companyfacts, US_GAAP_CONCEPTS["operating_cash_flow"], annual_only=True
            ),
            "capex_millions": latest_fact_value(
                companyfacts, US_GAAP_CONCEPTS["capex"], annual_only=True
            ),
            "depreciation_amortization_millions": latest_fact_value(
                companyfacts, US_GAAP_CONCEPTS["depreciation_amortization"], annual_only=True
            ),
            "cash_and_equivalents_millions": latest_fact_value(
                companyfacts, US_GAAP_CONCEPTS["cash_and_equivalents"]
            ),
            "total_assets_millions": latest_fact_value(companyfacts, US_GAAP_CONCEPTS["total_assets"]),
            "current_assets_millions": current_assets,
            "current_liabilities_millions": current_liabilities,
            "total_equity_millions": latest_fact_value(companyfacts, US_GAAP_CONCEPTS["total_equity"]),
            "shares_outstanding_millions": round(shares, 2) if shares is not None else None,
            "current_ratio": round(current_assets / current_liabilities, 2)
            if current_assets is not None and current_liabilities not in (None, 0)
            else None,
        },
        "_source": "sec companyfacts",
    }


def parse_submissions(submissions: dict) -> dict:
    recent = submissions.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    accession_numbers = recent.get("accessionNumber", [])
    filing_dates = recent.get("filingDate", [])

    latest_10k = None
    latest_10q = None
    for index, form in enumerate(forms):
        if latest_10k is None and form == "10-K":
            latest_10k = {
                "accession_number": accession_numbers[index],
                "filing_date": filing_dates[index],
            }
        if latest_10q is None and form == "10-Q":
            latest_10q = {
                "accession_number": accession_numbers[index],
                "filing_date": filing_dates[index],
            }
        if latest_10k and latest_10q:
            break

    return {
        "cik": zero_pad_cik(submissions.get("cik", "")),
        "company_name": submissions.get("name"),
        "tickers": submissions.get("tickers", []),
        "exchanges": submissions.get("exchanges", []),
        "latest_10k": latest_10k,
        "latest_10q": latest_10q,
        "_source": "sec submissions",
    }


def build_report_from_sec(ticker: str, tickers_payload: dict, submissions: dict, companyfacts: dict) -> dict:
    cik = resolve_ticker_to_cik(ticker, tickers_payload)
    return {
        "ticker": ticker.upper(),
        "resolved_cik": cik,
        "submissions": parse_submissions(submissions),
        "companyfacts": parse_companyfacts(companyfacts),
    }


def main():
    parser = argparse.ArgumentParser(description="Parse SEC submissions and companyfacts into a simplified report.")
    parser.add_argument("ticker")
    parser.add_argument("--tickers", required=True, help="Path or URL for SEC company_tickers.json")
    parser.add_argument("--submissions", required=True, help="Path or URL for SEC submissions JSON")
    parser.add_argument("--companyfacts", required=True, help="Path or URL for SEC companyfacts JSON")
    parser.add_argument("--user-agent", default=DEFAULT_USER_AGENT)
    args = parser.parse_args()

    tickers_payload = load_json_input(args.tickers, user_agent=args.user_agent)
    submissions_payload = load_json_input(args.submissions, user_agent=args.user_agent)
    companyfacts_payload = load_json_input(args.companyfacts, user_agent=args.user_agent)
    report = build_report_from_sec(args.ticker, tickers_payload, submissions_payload, companyfacts_payload)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
