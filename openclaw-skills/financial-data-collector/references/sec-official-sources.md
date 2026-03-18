# SEC Official Sources

Use official SEC endpoints before third-party summaries when checking filings or XBRL facts.

## Key endpoints

- `https://www.sec.gov/files/company_tickers.json`
- `https://data.sec.gov/submissions/CIK##########.json`
- `https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json`

## Why they matter

- filings and XBRL facts come directly from the SEC
- no API key is required
- updates happen as filings are disseminated

## Practical usage

- use `company_tickers.json` to map ticker to CIK
- use `submissions` to identify recent 10-K and 10-Q filings
- use `companyfacts` for normalized XBRL facts across filings

Always include a descriptive user agent string for automated requests.

