# Salary Plus Side Business Guide

Purpose: Read this when salary income and business income must be filed together. This file covers accrual timing, mixed personal/business accounts, duplicate-deduction traps, and sanity checks for the final tax result.

## Contents

- [Accrual timing and year-end receivables](#accrual-timing-and-year-end-receivables)
- [Personal-account bookkeeping patterns](#personal-account-bookkeeping-patterns)
- [IT and software-development expenses](#it-and-software-development-expenses)
- [Duplicate-deduction checklist](#duplicate-deduction-checklist)
- [Tax-result sanity check](#tax-result-sanity-check)

## Accrual Timing and Year-End Receivables

### Core Rule

Under `所得税法第36条`, revenue is recognized when the right to receive it becomes fixed.

| Timing basis | Recognition point | Example |
|--------------|-------------------|---------|
| Service-delivery basis | The year in which the service is delivered | Consulting performed in December -> that year’s revenue |
| Invoice-date basis | The invoice issue date | Use only if it matches the actual recognition rule |
| Inspection-acceptance basis | The date the work is accepted | Use consistently if contract terms require it |

> Use one consistent basis that matches the contract facts. Do not change the basis between years without a clear reason.

### Year-End Receivable Patterns

| Pattern | Journal entry | Filing year |
|---------|---------------|-------------|
| Service in December, invoice/payment in January | `売掛金 / 売上高` | Current year revenue |
| Service in previous December, payment in current January | `普通預金 / 売掛金` | Previous year revenue only |
| Service and payment both in December | `普通預金 / 売上高` | Current year revenue |

### Checklist to Avoid Mixing Prior-Year Revenue

1. Confirm the prior-year year-end receivable balance.
2. Identify January and February collections that belong to prior-year receivables.
3. Confirm those collections are not included again in current-year revenue.

```text
【12月: 役務提供時（売上計上）】
  売掛金 XXX,XXX / 売上高 XXX,XXX

【翌年1月: 入金時（売掛金回収）】
  普通預金 XXX,XXX / 売掛金 XXX,XXX
  ※翌年の売上ではなく、売掛金の回収
```

## Personal-Account Bookkeeping Patterns

Use `事業主貸` and `事業主借` when the taxpayer does not keep a dedicated business account.

### Which Account to Use

| Account | Direction | Typical use |
|---------|-----------|-------------|
| `事業主貸` | Business -> personal | Revenue landing in a personal account, private spending from business funds |
| `事業主借` | Personal -> business | Business expense paid from personal funds |

### Common Patterns

```text
【パターン1: 個人口座に事業売上が入金】
  事業主貸 XXX,XXX / 売上高 XXX,XXX

【パターン2: 個人口座に売掛金が入金（源泉徴収あり）】
  事業主貸 XXX,XXX / 売掛金 XXX,XXX
  事業主貸  XX,XXX     （源泉徴収税額分）

【パターン3: 個人口座・個人クレカで事業経費を支払い】
  通信費 X,XXX / 事業主借 X,XXX

【パターン4: 個人口座から家賃引落し（按分あり）】
  地代家賃 XX,XXX / 事業主借 XXX,XXX
  事業主貸 XX,XXX

【パターン5: 事業用クレカで個人的な買い物】
  事業主貸 X,XXX / 未払金 X,XXX
```

### Year-End Handling

```text
事業主貸と事業主借は損益に影響しない資本の勘定科目。
期末に残高をそのまま貸借対照表に記載する。

翌期首の元入金への振替:
  元入金(翌期首) = 元入金(前期末) + 事業主借(前期末) - 事業主貸(前期末) + 所得(前期)
```

## IT and Software-Development Expenses

### Recommended Account Mapping

| Spending | Recommended account | e-Tax bucket | Notes |
|----------|---------------------|--------------|-------|
| SaaS fees such as GitHub, AWS, or Figma | `支払手数料` | Optional account | Cloud and platform usage fees |
| Internet connection | `通信費` | Standard account 12 | Allocate between business and private use |
| Mobile phone | `通信費` | Standard account 12 | Allocate if mixed use |
| Technical books and e-books | `新聞図書費` | Optional account | Directly related to the business |
| Conferences and online training | `研修費` | Optional account | Skill-building cost |
| PC or display over JPY 100,000 | `減価償却費` | Standard account 18 | PC useful life is usually four years |
| Peripherals under JPY 100,000 | `消耗品費` | Standard account 17 | Expense immediately |
| Coworking fee | `地代家賃` | Standard account 23 | Monthly location fee |
| Domain and hosting | `支払手数料` or `通信費` | Optional or standard | Keep the choice consistent |
| Outsourced design or translation work | `外注工賃` | Standard account 21 | Check withholding obligations |

### Allocation Ranges Often Seen in Side Businesses

| Cost | Typical range | Logic |
|------|---------------|-------|
| Internet | 30% to 50% | Business-use time over total use time |
| Mobile phone | 20% to 40% | Business calls and data use |
| Home rent | 10% to 30% | Workspace share times usage time |
| Electricity | 10% to 30% | Space or time basis |
| Mixed-use PC | 50% to 80% | Business-use time share |

> These are only rough guides. The user still needs a reasonable factual basis that can be explained later.

## Duplicate-Deduction Checklist

This is one of the highest-value checks in salary-plus-side-business filing.

| # | Item | Check on the withholding slip | Return input |
|---|------|-------------------------------|--------------|
| 1 | Basic deduction | — | Usually automatic, do not add manually |
| 2 | Social-insurance deduction from salary withholding | `社会保険料等の金額` | Do not input again |
| 3 | Additional social-insurance payments such as extra pension | Certificate | Input separately |
| 4 | Life-insurance deduction | `生命保険料の控除額` | Do not input again if already reflected |
| 5 | Earthquake-insurance deduction | `地震保険料の控除額` | Do not input again if already reflected |
| 6 | Spouse deduction | Withholding-slip entry | Do not input again |
| 7 | Dependent deduction | Withholding-slip entry | Do not input again |
| 8 | iDeCo contributions | Breakdown of `社会保険料等の金額` | Add only if paid personally, not via employer |
| 9 | Medical-expense deduction | — | Input in the final return |
| 10 | Furusato Nozei | — | Input every municipality in the final return |
| 11 | Housing-loan credit after year 2 | `住宅借入金等特別控除の額` | Usually already reflected |
| 12 | First-year housing-loan credit | — | Input in the final return |

### Why This Matters

- Overstated income deductions can create additional tax and `過少申告加算税` risk.
- Overstated tax credits create the same downstream risk.
- e-Tax catches only some duplicate-input patterns.

## Tax-Result Sanity Check

### Combined Calculation Flow

```text
Step 1: Employment income
  salary revenue - employment-income deduction = employment income

Step 2: Business income
  business revenue - necessary expenses - blue filing special deduction = business income

Step 3: Total income
  employment income + business income = total income
  Apply the employment-income adjustment if it is relevant.

Step 4: Taxable income
  total income - total deductions = taxable income

Step 5: Income tax
  taxable income x rate - quick deduction = calculated income tax

Step 6: Tax credits
  calculated income tax - tax credits = base income tax

Step 7: Reconstruction special income tax
  base income tax x 2.1% = reconstruction tax

Step 8: Final filing result
  (base income tax + reconstruction tax) - withholding tax = final payable/refundable amount
```

### Quick Reasonableness Check

```text
Approximate additional tax ≒ business income x marginal rate

Example:
  taxable income JPY 6 million
  national income-tax marginal rate 20%
  resident-tax rate about 10%
  rough total incremental burden ≒ 30% of side-business income
```

| Check | What to confirm |
|------|-----------------|
| Additional national income tax is roughly 15% to 33% of business income | Usually reasonable |
| Withholding tax was subtracted correctly | Compare with the withholding slip |
| Contractor withholding exists | Confirm it appears in `第二表` income detail |
| Furusato Nozei reflected | Confirm the donation deduction appears |
| Estimated tax exists | Confirm it is credited |

### Suspicious Signs

| Sign | Likely cause |
|------|--------------|
| Additional tax exceeds 50% of business income | Missing deductions or missing withholding credits |
| Additional tax is zero or negative despite profitable side business | Salary-income input may be missing |
| Resident-tax notice is far from expectation | Income or deduction input may be wrong |

> Use this file together with `references/e-tax-screen-guide.md` when the user needs screen-level instructions. Keep the final answer in Japanese and include the standard disclaimer.
