# Income Classification Reference

Purpose: Read this when the user needs income-type classification, comprehensive vs separate taxation, or loss-offset rules.

## Contents

- [Income categories](#income-categories)
- [Taxation method](#taxation-method)
- [Loss offset and carryforward](#loss-offset-and-carryforward)
- [Common patterns](#common-patterns)

## Income Categories

| # | Income type | Definition | Typical taxpayers | Taxation method |
|---|-------------|------------|-------------------|-----------------|
| 1 | Interest income (`利子所得`) | Interest on deposits and bonds | Depositors | Withholding separate taxation |
| 2 | Dividend income (`配当所得`) | Stock dividends and fund distributions | Investors | Comprehensive or separate by election |
| 3 | Real-estate income (`不動産所得`) | Rent from land or buildings | Landlords | Comprehensive |
| 4 | Business income (`事業所得`) | Income from a business | Freelancers and sole proprietors | Comprehensive |
| 5 | Employment income (`給与所得`) | Salary and bonuses | Employees | Comprehensive |
| 6 | Retirement income (`退職所得`) | Retirement allowances | Retirees | Separate |
| 7 | Forestry income (`山林所得`) | Sale of forest assets held for more than five years | Forest owners | Separate (`5分5乗方式`) |
| 8 | Capital gains (`譲渡所得`) | Gains on asset sales | Property or stock sellers | Comprehensive or separate |
| 9 | Temporary income (`一時所得`) | Prize winnings, insurance maturity proceeds, and similar windfalls | Individuals with one-off gains | Comprehensive (`1/2` inclusion) |
| 10 | Miscellaneous income (`雑所得`) | Income not covered above | Side-business workers, pensioners | Comprehensive |

## Taxation Method

### Comprehensive Taxation

Apply progressive rates after combining eligible income types.

```text
Income amounts -> combine -> income deductions -> taxable income -> progressive rates
```

Typical categories: partial interest income, dividends when elected, real-estate income, business income, employment income, temporary income, and miscellaneous income.

### Separate Taxation

| Income | Rate | Notes |
|--------|------|-------|
| Listed-stock dividends | 20.315% | Income tax 15.315% + resident tax 5% |
| Listed-stock gains | 20.315% | Same as above |
| Short-term land/building gains | 39.63% | Held for five years or less |
| Long-term land/building gains | 20.315% | Held for more than five years |
| Futures trading | 20.315% | Separate group |
| Retirement income | Progressive rates | Calculated separately even though the rate is progressive |
| Forestry income | `5分5乗方式` | Separate regime |

### Withholding Separate Taxation

Applies mainly to deposit interest and similar products where withholding completes the taxation.

## Loss Offset and Carryforward

### Offsettable Losses

| Loss source | Offset against | Limits |
|-------------|----------------|--------|
| Business income | Most other income | Stock-transfer losses are excluded |
| Real-estate income | Most other income | Interest on debt for land acquisition is excluded |
| Forestry income | Most other income | — |
| Capital losses | Most other income | Household assets and listed stocks have special rules |

### Non-offsettable Losses

- Losses from dividends, employment income, temporary income, or miscellaneous income
- Losses on household assets
- Listed-stock losses outside the same separate-taxation group

### Offset Order

```text
1. Ordinary-income group (business / real estate with other ordinary income)
2. Capital-gain and temporary-income group
3. Cross-group offset
4. Forestry income and retirement income
```

### Carryforward

| Type | Carryforward period | Requirement |
|------|---------------------|-------------|
| Net operating loss | 3 years | Blue return required |
| Casualty loss | 3 years | Available even for white returns |
| Listed-stock transfer loss | 3 years | Filing required every year |
| Residential-property transfer loss | 3 years | Additional requirements apply |

## Common Patterns

### Freelancers and Sole Proprietors

```text
Business income = business revenue - necessary expenses - blue filing special deduction (up to JPY 650,000)
Taxable income = business income - income deductions
```

### Salary Earners with Side Work

| Side-work pattern | Typical income type | Main decision signal |
|-------------------|---------------------|----------------------|
| Ongoing contractor work | Business income or miscellaneous income | Whether it reaches business scale |
| One-off manuscript or speaking fee | Miscellaneous income | No continuity or business structure |
| Resale / marketplace trading | Business income or miscellaneous income | Profit motive and continuity |
| Rental income | Real-estate income | `5棟10室基準` and rental pattern |
| Stock investing | Dividend income + capital gains | Filing may be unnecessary in withholding accounts |
| Crypto assets | Miscellaneous income | Comprehensive taxation |

### Business Income vs Miscellaneous Income

Under the 2022 NTA clarification, decide based on whether the activity is socially recognized as a business:

- Books and supporting documents are maintained -> generally closer to business income unless strong contrary facts exist.
- Books and supporting documents are not maintained -> generally closer to miscellaneous income.
- Also consider the share of total income, time/effort spent, continuity, and business independence.

> Keep this as general guidance only. If the classification materially affects tax treatment and facts are disputed, respond as `L3` and recommend a tax accountant.
