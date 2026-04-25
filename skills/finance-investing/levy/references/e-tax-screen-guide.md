# e-Tax Screen Guide

Purpose: Read this when the user needs screen-by-screen guidance for `確定申告書等作成コーナー`, common error handling, or the recommended order of e-Tax inputs.

## Contents

- [Blue return financial statement](#blue-return-financial-statement)
- [Income-tax return screens](#income-tax-return-screens)
- [Common errors](#common-errors)
- [Screen order](#screen-order)

## Blue Return Financial Statement

### Monthly Sales Entry

Screen: `青色申告決算書 -> 売上（収入）金額の内訳`

| Field | What to enter | Important note |
|-------|---------------|----------------|
| Monthly sales (January to December) | Sales recognized in each month | Use the service-delivery month under the accrual basis |
| Total field | Leave blank | Manual input causes `KS-E20009` |

Common traps:

- Decide the month by service-delivery timing, not the payment date.
- Service delivered in December and billed in January still belongs to December sales.
- A January payment for prior-December work is collection of prior-year receivables, not current-year sales.

### Cost of Goods Sold

Screen: `青色申告決算書 -> 売上原価`

| Field | Typical handling for IT / software development |
|-------|-----------------------------------------------|
| Opening inventory | Leave blank |
| Purchases | Leave blank |
| Closing inventory | Leave blank |
| Cost of goods sold | Leave blank |

> Service businesses without inventory usually leave this section blank. Outsourcing belongs in `外注工賃`, not in inventory or purchases.

### Expense Entry

Screen: `青色申告決算書 -> 経費`

#### Standard Accounts (`8` to `24`)

| No. | Account | Common IT / software example |
|-----|---------|------------------------------|
| 8 | `租税公課` | Business tax, allocated fixed-asset tax, stamp tax |
| 10 | `水道光熱費` | Allocated electricity |
| 11 | `旅費交通費` | Meetings and business travel |
| 12 | `通信費` | Allocated internet and mobile phone |
| 13 | `広告宣伝費` | Portfolio-site costs |
| 14 | `接待交際費` | Client meals |
| 16 | `修繕費` | PC repairs |
| 17 | `消耗品費` | Items under JPY 100,000 |
| 18 | `減価償却費` | PC, display, and similar assets |
| 20 | `給料賃金` | Employee wages, if any |
| 21 | `外注工賃` | Outsourcing payments |
| 22 | `利子割引料` | Business-loan interest |
| 23 | `地代家賃` | Allocated home-office rent |
| 24 | `雑費` | Small uncategorized expenses |

#### Optional Accounts (`25` to `30`)

| Recommended account | Typical use |
|---------------------|-------------|
| `支払手数料` | SaaS or cloud-service fees |
| `新聞図書費` | Technical books and subscriptions |
| `研修費` | Conferences and courses |
| `諸会費` | Associations or coworking memberships |

> `支払手数料` is often the clearest bucket for SaaS costs because there is no dedicated standard account.

### Depreciation Detail Screen

Screen: `青色申告決算書 -> 経費 -> 減価償却費 -> 入力`

| Field | Entry | Note |
|-------|-------|------|
| Asset name | Clear asset label | Example: laptop, monitor |
| Acquisition date | Purchase date | Count the acquisition month as one month |
| Acquisition cost | Purchase amount | Follow the taxpayer’s accounting basis |
| Method | Usually straight-line | Sole-proprietor default unless another method was elected |
| Useful life | Asset-specific years | PC `4`, software `5` |
| Current-year depreciation | `cost x rate x months / 12` | Monthly proration applies |
| Business-use ratio | Allocation percentage | `100` if fully business-use |
| Expense amount | Depreciation x business ratio | Sometimes auto-calculated |
| Undepreciated balance | Cost minus accumulated depreciation | Keep consistent with ledgers |

Low-cost asset rules:

- Blue-filer special rule under JPY 300,000 -> choose the applicable special treatment and expense immediately.
- JPY 100,000 to under JPY 200,000 -> use the three-year equal-depreciation path.

### Balance Sheet

Screen: `青色申告決算書 -> 貸借対照表`

| Area | What to keep aligned |
|------|----------------------|
| Assets | `現金`, `普通預金`, `売掛金`, `工具器具備品`, and similar year-end balances |
| Liabilities | `未払金`, `預り金`, and other year-end balances |
| Capital side | `元入金`, `事業主貸`, `事業主借`, and current-year result |

Important checks:

1. Fixed assets must be entered at book value, not acquisition cost.
2. `事業主貸` and `事業主借` should reflect the full-year totals if personal accounts were used.
3. `資産合計 = 負債合計 + 資本合計` must balance.
4. A difference of one to a few yen may come from rounding; larger gaps usually mean missing or duplicated entries.

## Income-Tax Return Screens

### Select Income Types

Screen: `確定申告書等作成コーナー -> 所得の種類を選択`

| Check item | When to select it |
|------------|-------------------|
| `給与所得` | Salary or wages exist |
| `事業所得` | Business revenue exists |
| `不動産所得` | Rent revenue exists |
| `雑所得` | Miscellaneous side income or pension income exists |
| `配当所得` | Dividend income is being filed under comprehensive taxation |

Most important trap: in salary-plus-side-business cases, keep both `給与所得` and `事業所得`. Selecting only business income can understate tax materially.

### Withholding Slip Input

Screen: `確定申告書 -> 給与所得 -> 源泉徴収票の入力`

| Withholding-slip field | e-Tax field | Note |
|------------------------|-------------|------|
| `支払金額` | Revenue | Copy directly |
| `給与所得控除後の金額` | Income amount | If blank, year-end adjustment may be unfinished |
| `所得控除の額の合計額` | Total deductions | Already reflected in the slip |
| `源泉徴収税額` | Withholding tax | Credit against final tax |
| `社会保険料等の金額` | Social-insurance deduction | Usually already reflected |
| `生命保険料の控除額` | Life-insurance deduction | Use the deduction amount |
| `地震保険料の控除額` | Earthquake-insurance deduction | Use the deduction amount |
| `住宅借入金等特別控除の額` | Housing-loan credit | Tax-credit item |
| Spouse and dependent entries | Matching deduction fields | Transfer consistently |

If the screen also asks for insurance-premium amounts, the deduction certificate may still be needed in addition to the withholding slip.

### Deduction Input

Screen: `確定申告書 -> 所得控除の入力`

Keep this rule explicit: do not input again what was already processed on the withholding slip.

| Deduction | Usually already processed on the slip? | Return input |
|-----------|----------------------------------------|--------------|
| Basic deduction | Yes | Usually no manual input |
| Spouse deduction | Yes | Do not duplicate |
| Dependent deduction | Yes | Do not duplicate |
| Social insurance withheld from salary | Yes | Do not duplicate |
| Life-insurance deduction | Yes | Do not duplicate |
| Earthquake-insurance deduction | Yes | Do not duplicate |
| Additional social-insurance payments | No | Add in the return |
| Medical-expense deduction | No | Add in the return |
| Donation deduction | No | Add in the return |
| iDeCo | Depends | Check whether the employer already reflected it |

### Dependents

Screen: `確定申告書 -> 配偶者・扶養親族の入力`

| Category | Income-tax deduction? | e-Tax handling |
|----------|-----------------------|----------------|
| Dependents age 16 and older | Yes | Enter as normal dependents |
| Dependents under 16 | No | Still enter them in `住民税に関する事項` |

### Furusato Nozei

Screen: `確定申告書 -> 寄附金控除の入力`

Most important trap: once a final return is filed, every one-stop filing becomes invalid.

| Situation | What to do |
|-----------|------------|
| One-stop filing was submitted | Re-enter every municipality in the return |
| No one-stop filing was submitted | Enter every municipality normally |

`xml` import through My Number Portal may help, but support depends on the platform.

### Resident-Tax Collection Method

Screen: `確定申告書 -> 住民税に関する事項 -> 給与、公的年金等以外の所得に係る住民税の徴収方法`

| Option | Meaning | Typical consequence |
|--------|---------|---------------------|
| `自分で納付` (`普通徴収`) | Pay the resident tax on non-salary income directly | May reduce visibility of side income to the employer |
| `給与から差引き` (`特別徴収`) | All resident tax is withheld from salary | The employer may infer side income from the higher amount |

> Some municipalities still combine everything into special collection even when ordinary collection is requested.

### Employment-Income Adjustment Check

Screen: salary input flow, usually auto-detected

If salary income exceeds JPY 8.5 million, confirm whether the conditions for the employment-income adjustment are reflected.

## Common Errors

| Error or issue | Likely cause | What to do |
|----------------|-------------|------------|
| `KS-E20009` | Manual input in the monthly-sales total field | Leave the total blank and let e-Tax calculate it |
| Balance sheet does not match | Missing entry or rounding difference | Small gaps can be adjusted with `事業主貸/借`; large gaps need a ledger review |
| Deduction amount differs from the withholding slip | Duplicate deduction input | Check whether the slip already reflected the deduction |
| Income tax is too high or too low | Salary-income input may be missing | Confirm both salary and business income were selected |
| Furusato Nozei does not reduce tax | One-stop filing misunderstanding | Enter every municipality in the return |
| Depreciation is missing from expenses | Detail screen not completed | Open the depreciation detail screen and enter each asset |
| Under-16 dependent effect is missing | Resident-tax screen entry missing | Enter the child in `住民税に関する事項` |
| e-Tax differs from manual calculation by JPY 1 | Rounding rules differ | Prefer the e-Tax result |
| Business expenses show as zero | `青色申告決算書` was not completed first | Complete the blue-return statement before the final return |

## Screen Order

```text
1. Start the return
2. Choose income tax and the submission method
3. If business income exists, complete 青色申告決算書 first:
   - monthly sales
   - cost of goods sold
   - expenses
   - depreciation detail
   - balance sheet
4. Move to the final return:
   - select income types
   - input salary from 源泉徴収票
   - confirm business income transfer
   - input deductions and tax credits
   - input dependents and resident-tax items
   - review the tax result
   - submit
```

> Use this file only for screen navigation. For combined-filing reasoning and overlap checks, pair it with `references/salary-plus-side-business.md`.
