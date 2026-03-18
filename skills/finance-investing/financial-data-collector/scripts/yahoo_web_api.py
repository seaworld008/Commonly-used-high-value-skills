#!/usr/bin/env python3

import json
import ssl
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


DEFAULT_USER_AGENT = "CodexFinanceSkills/1.0 finance-research@example.com"
QUOTE_SUMMARY_URL = "https://query1.finance.yahoo.com/v10/finance/quoteSummary/{ticker}?{query}"
TNX_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/%5ETNX?range=5d&interval=1d"


def raw_value(node):
    if isinstance(node, dict) and "raw" in node:
        return node["raw"]
    return node


def fetch_json(url: str, user_agent: str = DEFAULT_USER_AGENT) -> dict:
    request = Request(url, headers={"User-Agent": user_agent})
    context = ssl.create_default_context()
    with urlopen(request, context=context, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def load_json_input(path_or_url: str, user_agent: str = DEFAULT_USER_AGENT) -> dict:
    if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
        return fetch_json(path_or_url, user_agent=user_agent)
    return json.loads(Path(path_or_url).read_text(encoding="utf-8"))


def build_quote_summary_url(ticker: str) -> str:
    modules = ",".join(
        [
            "price",
            "defaultKeyStatistics",
            "financialData",
            "incomeStatementHistory",
            "cashflowStatementHistory",
            "balanceSheetHistory",
            "earningsTrend",
        ]
    )
    return QUOTE_SUMMARY_URL.format(ticker=ticker, query=urlencode({"modules": modules}))


def fetch_quote_summary(ticker: str, user_agent: str = DEFAULT_USER_AGENT) -> dict:
    return fetch_json(build_quote_summary_url(ticker), user_agent=user_agent)


def fetch_treasury_chart(user_agent: str = DEFAULT_USER_AGENT) -> dict:
    return fetch_json(TNX_CHART_URL, user_agent=user_agent)


def statement_entries(payload: dict, key: str) -> list[dict]:
    result = payload.get("quoteSummary", {}).get("result", [])
    if not result:
        return []
    statement = result[0].get(key, {})
    history = statement.get("incomeStatementHistory") or statement.get("cashflowStatements") or statement.get(
        "balanceSheetStatements"
    )
    return history or []


def quote_result(payload: dict) -> dict:
    result = payload.get("quoteSummary", {}).get("result", [])
    return result[0] if result else {}


def entries_by_year(entries: list[dict]) -> dict[int, dict]:
    mapped = {}
    for entry in entries:
        end_date = entry.get("endDate", {})
        year = raw_value(end_date)
        if isinstance(year, str):
            year = int(year[:4])
        elif isinstance(year, (int, float)):
            year = int(year)
        if year:
            mapped[year] = entry
    return mapped


def millions(value):
    numeric = raw_value(value)
    if numeric is None:
        return None
    return round(float(numeric) / 1_000_000, 2)


def parse_market_data(result: dict) -> dict:
    price = result.get("price", {})
    stats = result.get("defaultKeyStatistics", {})
    current_price = raw_value(price.get("regularMarketPrice"))
    shares = raw_value(stats.get("sharesOutstanding"))
    market_cap = raw_value(price.get("marketCap"))
    beta = raw_value(stats.get("beta"))
    return {
        "current_price": round(float(current_price), 2) if current_price is not None else None,
        "shares_outstanding_millions": round(float(shares) / 1_000_000, 2) if shares is not None else None,
        "market_cap_millions": round(float(market_cap) / 1_000_000, 2) if market_cap is not None else None,
        "beta_5y_monthly": round(float(beta), 3) if beta is not None else None,
    }


def parse_income_statement(result: dict, years: list[int]) -> tuple[dict, list[int]]:
    entries = entries_by_year(result.get("incomeStatementHistory", {}).get("incomeStatementHistory", []))
    parsed = {}
    missing = []
    for year in years:
        entry = entries.get(year)
        if not entry:
            parsed[str(year)] = {"_source": f"yahoo web has no statement for {year}"}
            missing.append(year)
            continue
        parsed[str(year)] = {
            "revenue": millions(entry.get("totalRevenue")),
            "ebit": millions(entry.get("operatingIncome")),
            "ebitda": millions(entry.get("ebitda")),
            "tax_expense": millions(entry.get("incomeTaxExpense")),
            "net_income": millions(entry.get("netIncome")),
            "_source": "yahoo web quoteSummary",
        }
    return parsed, missing


def parse_cash_flow(result: dict, years: list[int]) -> tuple[dict, list[int]]:
    entries = entries_by_year(result.get("cashflowStatementHistory", {}).get("cashflowStatements", []))
    parsed = {}
    missing = []
    for year in years:
        entry = entries.get(year)
        if not entry:
            parsed[str(year)] = {"_source": f"yahoo web has no statement for {year}"}
            missing.append(year)
            continue
        parsed[str(year)] = {
            "operating_cash_flow": millions(entry.get("totalCashFromOperatingActivities")),
            "capex": millions(entry.get("capitalExpenditures")),
            "depreciation_amortization": millions(entry.get("depreciation")),
            "free_cash_flow": millions(entry.get("freeCashFlow")),
            "change_in_nwc": millions(entry.get("changeToWorkingCapital")),
            "sbc": millions(entry.get("stockBasedCompensation")),
            "_source": "yahoo web quoteSummary",
        }
    return parsed, missing


def parse_balance_sheet(result: dict, latest_year: int) -> dict:
    entries = entries_by_year(result.get("balanceSheetHistory", {}).get("balanceSheetStatements", []))
    entry = entries.get(latest_year)
    if not entry:
        return {str(latest_year): {"_source": f"yahoo web has no statement for {latest_year}"}}
    total_debt = raw_value(entry.get("longTermDebt"))
    short_debt = raw_value(entry.get("shortLongTermDebt"))
    if total_debt is not None or short_debt is not None:
        total_debt = float(total_debt or 0) + float(short_debt or 0)
    cash = raw_value(entry.get("cash"))
    short_term_investments = raw_value(entry.get("shortTermInvestments"))
    cash_equiv = None
    if cash is not None or short_term_investments is not None:
        cash_equiv = float(cash or 0) + float(short_term_investments or 0)
    net_debt = total_debt - cash_equiv if total_debt is not None and cash_equiv is not None else None
    return {
        str(latest_year): {
            "total_debt": round(total_debt / 1_000_000, 2) if total_debt is not None else None,
            "cash_and_equivalents": round(cash_equiv / 1_000_000, 2) if cash_equiv is not None else None,
            "net_debt": round(net_debt / 1_000_000, 2) if net_debt is not None else None,
            "current_assets": millions(entry.get("totalCurrentAssets")),
            "current_liabilities": millions(entry.get("totalCurrentLiabilities")),
            "total_assets": millions(entry.get("totalAssets")),
            "total_equity": millions(entry.get("totalStockholderEquity")),
            "_source": "yahoo web quoteSummary",
        }
    }


def parse_analyst_estimates(result: dict) -> dict:
    estimates = {
        "revenue_next_fy": None,
        "revenue_fy_after": None,
        "eps_next_fy": None,
        "revenue_growth_next_year_pct": None,
        "_source": "missing",
    }
    trend = result.get("earningsTrend", {}).get("trend", [])
    current_fy = next((item for item in trend if item.get("period") == "0y"), None)
    next_fy = next((item for item in trend if item.get("period") == "+1y"), None)
    if current_fy or next_fy:
        if current_fy:
            estimates["eps_next_fy"] = raw_value(current_fy.get("earningsEstimate", {}).get("avg"))
            estimates["revenue_next_fy"] = millions(current_fy.get("revenueEstimate", {}).get("avg"))
        if next_fy:
            estimates["revenue_fy_after"] = millions(next_fy.get("revenueEstimate", {}).get("avg"))
            growth = raw_value(next_fy.get("growth"))
            estimates["revenue_growth_next_year_pct"] = round(float(growth) * 100, 2) if growth is not None else None
        estimates["_source"] = "yahoo web earningsTrend"
    return estimates


def parse_quote_summary(ticker: str, payload: dict, years: list[int]) -> dict:
    result = quote_result(payload)
    latest_year = max(years)
    market_data = parse_market_data(result)
    income_statement, income_missing = parse_income_statement(result, years)
    cash_flow, cash_missing = parse_cash_flow(result, years)
    return {
        "ticker": ticker.upper(),
        "company_name": result.get("price", {}).get("longName") or ticker.upper(),
        "market_data": market_data,
        "income_statement": income_statement,
        "cash_flow": cash_flow,
        "balance_sheet": parse_balance_sheet(result, latest_year),
        "analyst_estimates": parse_analyst_estimates(result),
        "metadata": {
            "_source": "yahoo web quoteSummary",
            "_nan_years": sorted(set(income_missing + cash_missing)),
        },
    }


def parse_treasury_chart(payload: dict) -> float | None:
    result = payload.get("chart", {}).get("result", [])
    if not result:
        return None
    closes = result[0].get("indicators", {}).get("quote", [{}])[0].get("close", [])
    closes = [value for value in closes if value is not None]
    if not closes:
        return None
    return round(float(closes[-1]) / 100, 4)
