# Tax Calculation Reference

Purpose: Read this when the user needs tax formulas, rate tables, resident tax, business tax, consumption-tax thresholds, or a sanity check for combined salary and business income.

## Contents

- [Calculation flow](#calculation-flow)
- [Income-tax rate table](#income-tax-rate-table)
- [Employment-income adjustment](#employment-income-adjustment)
- [Salary plus business example flow](#salary-plus-business-example-flow)
- [Resident tax](#resident-tax)
- [Business tax](#business-tax)
- [Consumption tax](#consumption-tax)
- [Effective-rate guide](#effective-rate-guide)

## Calculation Flow

```text
Step 1: Calculate each income amount
  revenue - necessary expenses (or employment-income deduction) = income amount

Step 2: Calculate total income
  combine comprehensive-taxation income -> apply loss offset -> apply carryforward = total income

Step 3: Calculate taxable income
  total income - income deductions = taxable income

Step 4: Calculate income tax
  taxable income x rate - quick deduction = calculated income tax

Step 5: Apply tax credits
  calculated income tax - tax credits = base income tax

Step 6: Add reconstruction special income tax
  base income tax x 2.1% = reconstruction tax
  base income tax + reconstruction tax = total national income tax

Step 7: Calculate the filing result
  total national income tax - withholding tax - estimated tax = final payable/refundable amount
```

## Income-Tax Rate Table

| Taxable income | Rate | Quick deduction |
|----------------|------|-----------------|
| Up to JPY 1.949 million | 5% | JPY 0 |
| JPY 1.95 million to JPY 3.299 million | 10% | JPY 97,500 |
| JPY 3.3 million to JPY 6.949 million | 20% | JPY 427,500 |
| JPY 6.95 million to JPY 8.999 million | 23% | JPY 636,000 |
| JPY 9 million to JPY 17.999 million | 33% | JPY 1,536,000 |
| JPY 18 million to JPY 39.999 million | 40% | JPY 2,796,000 |
| JPY 40 million and above | 45% | JPY 4,796,000 |

### Example

For taxable income of JPY 5 million:

```text
JPY 5,000,000 x 20% - JPY 427,500 = JPY 572,500 (income tax)
JPY 572,500 x 2.1% = JPY 12,022 (reconstruction special income tax)
Total: JPY 584,500 after truncation below JPY 100
```

## Reconstruction Special Income Tax

- Rate: `base income tax x 2.1%`
- Period: 2013 through 2037
- Withholding often already includes the add-on rate, for example `15.315%`

## Employment-Income Adjustment

Apply when salary income exceeds JPY 8.5 million and the statutory condition is met.

| Condition | Amount |
|-----------|--------|
| Taxpayer is specially disabled | `(salary income - JPY 8.5 million) x 10%`, capped at JPY 150,000 |
| Has a dependent under 23 | Same |
| Has a specially disabled spouse or dependent | Same |

> This adjustment belongs in the salary-income calculation, not in the income-deduction stage.

## Salary Plus Business Example Flow

```text
Step 1: Employment income
  salary revenue - employment-income deduction = employment income
  If salary revenue exceeds JPY 8.5 million, confirm the employment-income adjustment.

Step 2: Business income
  business revenue - necessary expenses - blue filing special deduction = business income

Step 3: Total income
  employment income + business income = total income

Step 4: Income deductions
  basic deduction + social-insurance deduction + other deductions = total deductions
  Separate items already reflected in the withholding slip from items that must be added in the return.

Step 5: Taxable income
  total income - total deductions = taxable income

Step 6: Calculated income tax
  taxable income x rate - quick deduction = calculated income tax

Step 7: Final filing result
  calculated income tax + reconstruction tax - withholding tax = final payable/refundable amount
```

### Sanity Check for Additional Tax

```text
Approximate additional national income tax ≒ business income x marginal tax rate

Marginal rate = the rate bracket reached after combining salary income and business income
Example:
  combined taxable income JPY 6 million -> marginal income-tax rate 20%
  business income JPY 1 million -> rough additional national income tax ≒ JPY 200,000
```

| Check | Interpretation |
|------|----------------|
| Additional tax is roughly 15% to 33% of business income | Usually within the normal range for national income tax only |
| Additional tax exceeds 50% of business income | Recheck missing deductions or missing withholding credits |
| Additional tax is zero or negative despite profitable side business | Recheck salary-income input and withholding data |

For detailed combined-filing traps, load `references/salary-plus-side-business.md`.

## Employment-Income Deduction

| Salary revenue | Deduction |
|----------------|-----------|
| Up to JPY 1.625 million | JPY 550,000 |
| Over JPY 1.625 million to JPY 1.8 million | Revenue x 40% - JPY 100,000 |
| Over JPY 1.8 million to JPY 3.6 million | Revenue x 30% + JPY 80,000 |
| Over JPY 3.6 million to JPY 6.6 million | Revenue x 20% + JPY 440,000 |
| Over JPY 6.6 million to JPY 8.5 million | Revenue x 10% + JPY 1.1 million |
| Over JPY 8.5 million | JPY 1.95 million |

## Public-Pension Deduction

| Age | Pension revenue | Deduction |
|-----|-----------------|-----------|
| Under 65 | Up to JPY 1.3 million | JPY 600,000 |
| 65 or older | Up to JPY 3.3 million | JPY 1.1 million |

> The deduction is phased down if non-pension income exceeds JPY 10 million.

## Resident Tax

### Overview

| Item | Content |
|------|---------|
| Taxing authority | Prefecture plus municipality |
| Reference date | Address as of January 1 |
| Rate | 10% income-based levy plus per-capita levy |
| Per-capita levy | Roughly JPY 5,000 per year, depending on the municipality |

### Main Differences from Income Tax

| Item | Income tax | Resident tax |
|------|------------|--------------|
| Basic deduction | JPY 480,000 | JPY 430,000 |
| Spouse deduction | JPY 380,000 | JPY 330,000 |
| General dependent deduction | JPY 380,000 | JPY 330,000 |
| Rate | 5% to 45% progressive | 10% flat income levy |
| Filing method | Self-assessment | Assessed by the municipality |

### Furusato Nozei Resident-Tax Relief

```text
Basic resident-tax reduction = (donation - JPY 2,000) x 10%
Special resident-tax reduction = (donation - JPY 2,000) x (100% - 10% - income-tax rate x 1.021)
The special part is capped at 20% of resident-tax income levy.
```

## Business Tax

| Item | Content |
|------|---------|
| Tax base | Statutory business categories |
| Rate | 3% to 5% for most categories |
| Deduction | JPY 2.9 million business-owner deduction |
| Formula | `(business income - JPY 2.9 million) x rate` |
| Payment timing | Usually two installments in August and November |

### Common Non-Taxable Example

Writers, cartoonists, musicians, and some programmers may fall outside the taxable categories, but contract software development can still be treated as `請負業` depending on the prefecture.

## Consumption Tax

### Taxable-Business Threshold

| Test | Result |
|------|--------|
| Taxable sales in the base period (two years prior) exceed JPY 10 million | Taxable business |
| Taxable sales in the specified period (January 1 to June 30 of the prior year) exceed JPY 10 million | Taxable business |
| Invoice registration is completed | Taxable business regardless of revenue |

### Simplified Taxation

| Deemed purchase rate | Business category |
|----------------------|------------------|
| 90% | Wholesale |
| 80% | Retail |
| 70% | Manufacturing and similar |
| 60% | Other categories |
| 50% | Services and similar |
| 40% | Real estate |

- Requirement: taxable sales in the base period are JPY 50 million or less, plus a valid election.
- Freelancers in service businesses usually fall into the 50% category.

### 20% Transitional Rule

- Applies to businesses that became taxable due to invoice registration.
- Transitional period: from October 2023 through September 2026.
- Formula: `output tax x 20%`

## Effective-Rate Guide

| Taxable income | Income-tax rate | Resident-tax rate | Approximate total |
|----------------|-----------------|-------------------|-------------------|
| JPY 2 million | about 5.1% | 10% | about 15% |
| JPY 4 million | about 10.4% | 10% | about 20% |
| JPY 6 million | about 13.7% | 10% | about 24% |
| JPY 8 million | about 16.5% | 10% | about 27% |
| JPY 10 million | about 20.4% | 10% | about 30% |

> These are rough guides assuming only the basic deduction. Actual effective rates move materially when deductions or tax credits change.
