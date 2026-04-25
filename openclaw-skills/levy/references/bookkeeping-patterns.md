# Bookkeeping Patterns Reference

Purpose: Read this when the user asks about ledgers, journal entries, household allocation, depreciation, or ledger-retention rules.

## Contents

- [Bookkeeping methods](#bookkeeping-methods)
- [Core accounts](#core-accounts)
- [Household allocation](#household-allocation)
- [Depreciation](#depreciation)
- [Common journal entries](#common-journal-entries)
- [Retention rules](#retention-rules)
- [Year-end issues](#year-end-issues)

## Bookkeeping Methods

| Item | Double-entry bookkeeping | Simple bookkeeping |
|------|--------------------------|--------------------|
| Blue filing special deduction | JPY 550,000 or JPY 650,000 | JPY 100,000 |
| Typical ledgers | `仕訳帳`, `総勘定元帳` | Cash book, receivable book, and similar simplified ledgers |
| Financial statements | Balance sheet plus profit and loss statement | Profit and loss statement only |
| Difficulty | Higher, often with accounting software | Lower |
| Best fit | Most sole proprietors with business income | Small-scale cases only |

## Core Accounts

### Asset Accounts

| Account | Meaning | Example |
|---------|---------|---------|
| `現金` | Business cash on hand | Cash used for business purchases |
| `普通預金` | Business bank account | Dedicated business account |
| `売掛金` | Uncollected sales | Issued invoice not yet paid |
| `前払費用` | Prepaid expense | Annual insurance premium |
| `工具器具備品` | Equipment and fixtures | PC, desk |
| `車両運搬具` | Business vehicle | Company car used for business |
| `事業主貸` | Transfer from business to personal side | Personal withdrawal |

### Liability and Equity-Like Accounts

| Account | Meaning | Example |
|---------|---------|---------|
| `買掛金` | Unpaid purchases | Supplier payable |
| `未払金` | Unpaid expense | Credit-card balance |
| `預り金` | Money temporarily held | Withholding tax from contractor income |
| `借入金` | Borrowed funds | Business loan |
| `事業主借` | Transfer from personal to business side | Personal money used for business |

### Revenue and Expense Accounts

| Account | Meaning | Mixed-use risk |
|---------|---------|----------------|
| `売上高` | Core business revenue | Low |
| `雑収入` | Incidental revenue | Medium |
| `水道光熱費` | Utilities | High |
| `通信費` | Internet, phone, postage | High |
| `旅費交通費` | Travel and transport | Low |
| `広告宣伝費` | Advertising and promotion | Low |
| `接待交際費` | Client meals and gifts | Low |
| `修繕費` | Repairs | Medium |
| `消耗品費` | Small tools and supplies | Medium |
| `減価償却費` | Depreciation expense | Medium |
| `外注工賃` | Outsourcing cost | Low |
| `地代家賃` | Office or mixed-use rent | High |
| `専従者給与` | Salary for eligible family workers | Requires advance filing |

## Household Allocation

Use a reasonable factual basis whenever business and private use are mixed.

### Common Bases

| Cost | Allocation basis | Formula idea |
|------|------------------|-------------|
| Rent | Floor-space ratio | Business area / total area |
| Utilities | Time or area ratio | Business use time / total time |
| Internet and phone | Usage ratio | Business communication volume / total volume |
| Vehicle | Distance ratio | Business distance / total distance |
| PC | Time ratio | Business-use time / total-use time |

### Typical Ranges in Home-Based Freelance Work

| Cost | Typical range | Example logic |
|------|---------------|--------------|
| Rent | 30% to 50% | Dedicated workspace ratio |
| Electricity | 30% to 50% | Usage-time ratio |
| Internet | 50% to 80% | Business-use ratio |
| Mobile phone | 50% to 70% | Business-call ratio |

> Keep supporting notes. An allocation without a documented rationale is weak.

## Depreciation

### Main Methods

| Method | Formula | Sole-proprietor default |
|--------|---------|-------------------------|
| Straight-line | Acquisition cost x straight-line rate | Default, no additional notice needed |
| Declining-balance | Undepreciated balance x rate | Requires the appropriate notice |

### Common Useful Lives

| Asset | Useful life | Straight-line rate |
|-------|-------------|--------------------|
| PC | 4 years | 0.250 |
| Desk or chair | 8 years (metal) / 5 years (wood) | 0.125 / 0.200 |
| Copier | 5 years | 0.200 |
| Standard passenger car | 6 years | 0.167 |
| Light vehicle | 4 years | 0.250 |
| Wooden building | 22 years | 0.046 |
| Reinforced-concrete building | 47 years | 0.022 |
| Self-used software | 5 years | 0.200 |

### Low-Cost Asset Rules

| Asset band | Handling | Requirement |
|------------|----------|-------------|
| Under JPY 100,000 | Expense immediately, usually `消耗品費` | Available to all filers |
| JPY 100,000 to under JPY 200,000 | Three-year equal depreciation | Available to all filers |
| JPY 100,000 to under JPY 300,000 | Expense immediately | Blue filers only, yearly cap JPY 3 million |

### Mid-Year Acquisition

```text
Depreciation = acquisition cost x rate x months used / 12
Count the acquisition month as one full month.
```

## Common Journal Entries

### Revenue

```text
【売上計上（請求書発行時）】
  売掛金 100,000 / 売上高 100,000

【入金時】
  普通預金 89,790 / 売掛金 100,000
  事業主貸 10,210     （源泉徴収税 10.21%）
```

### Expenses

```text
【事業用品を現金で購入】
  消耗品費 5,000 / 現金 5,000

【家賃を銀行振込（按分率40%）】
  地代家賃 40,000 / 普通預金 100,000
  事業主貸 60,000

【クレジットカード利用】
  通信費 3,000 / 未払金 3,000  ← 利用時
  未払金 3,000 / 普通預金 3,000  ← 引落時

【個人の口座から事業経費を支払い】
  消耗品費 10,000 / 事業主借 10,000
```

### Year-End Adjustments

```text
【減価償却（定額法）】
  減価償却費 62,500 / 工具器具備品 62,500
  （PC 250,000円、4年定額法: 250,000 × 0.250）

【家事按分の決算整理】
  事業主貸 72,000 / 水道光熱費 72,000
  （年間120,000円、事業按分率40%、個人分60%=72,000円を振替）
```

## Retention Rules

| Document | Retention period |
|----------|------------------|
| Ledgers such as `仕訳帳` and `総勘定元帳` | 7 years |
| Financial statements | 7 years |
| Invoices and receipts | 7 years, or 5 years when the prior-prior-year income is `<= JPY 3 million` |
| Other supporting documents | 5 years |

### Electronic Bookkeeping Storage Act

- Since January 1, 2024, electronic transaction data must generally be stored electronically.
- Emailed invoices and receipts should be kept as data, not only on paper.
- Searchability should cover transaction date, amount, and counterparty.

## Year-End Issues

### Personal-Account Use

If the taxpayer uses a personal account for business transactions, keep `事業主貸` and `事業主借` in the balance sheet and do not treat them as profit-and-loss items.

### Year-End Receivables

```text
【12月に役務提供、翌年1月に入金】
  (当年) 売掛金 XXX,XXX / 売上高 XXX,XXX
  (翌年) 普通預金 XXX,XXX / 売掛金 XXX,XXX

【前年12月に提供、当年1月に入金】
  当年の売上には含めない
```

Revenue follows the service or rights-fixation year, not the payment date.

### Fixed Assets on the Balance Sheet

```text
Book value = acquisition cost - accumulated depreciation

Example:
  PC acquisition cost JPY 250,000
  Straight-line, 4 years, end of year 2
  Accumulated depreciation = 250,000 x 0.250 x 2 = 125,000
  Book value = 125,000
```

### Rounding Differences

| Gap size | Handling |
|----------|----------|
| 1 to a few yen | Adjust with `事業主貸` or `事業主借` |
| Larger than that | Recheck missing or duplicated entries |

```text
【貸借対照表で資産側が1円多い場合】
  事業主貸 1 / [差異のある科目] 1

【貸借対照表で負債+資本側が1円多い場合】
  [差異のある科目] 1 / 事業主借 1
```

> Use `references/salary-plus-side-business.md` together with this file when the user is an employee with side business income and mixed personal/business accounts.
