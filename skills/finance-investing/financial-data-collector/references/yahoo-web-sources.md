# Yahoo Web Source Notes

This repository uses public Yahoo Finance web endpoints through Python standard library helpers so the default collection path does not require `yfinance` or `pandas`.

## What the low-dependency path covers

- quote and market cap
- shares outstanding
- beta
- annual income statement, cash flow, and balance sheet fields
- earnings trend and basic forward estimates
- 10Y Treasury yield via the Yahoo chart endpoint

## Why this helps

- lower setup friction in generic AI coding environments
- easier unit testing with local JSON fixtures
- keeps `yfinance` as an optional enhancement instead of a hard requirement

## Tradeoff management

The output schema stays the same even when engines differ. That means downstream skills do not need to know whether data came from the standard-library path or the optional `yfinance` adapter.

