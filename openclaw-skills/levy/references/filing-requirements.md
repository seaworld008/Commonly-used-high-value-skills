# Filing Requirement Reference

Purpose: Read this when the user needs a filing-required decision, the `20万円ルール`, refund-filing guidance, or penalty rules.

## Contents

- [Who must file](#who-must-file)
- [The 20万円 rule](#the-20万円-rule)
- [Salary earners with side work](#salary-earners-with-side-work)
- [Freelancers and sole proprietors](#freelancers-and-sole-proprietors)
- [Penalties and relief](#penalties-and-relief)
- [Refund filing](#refund-filing)
- [Pensioners](#pensioners)

## Who Must File

### Decision Flow

```text
Q1: Is the person mainly an employee?
├── Yes -> check the salary-earner conditions below
└── No -> check the non-salary conditions below

Salary-earner conditions:
├── Salary income exceeds JPY 20 million -> filing required
├── Salary from two or more employers -> filing may be required
├── Non-salary income exceeds JPY 200,000 -> filing required
├── Wants medical-expense deduction or similar refund-only deduction -> filing is beneficial
├── Wants first-year housing-loan deduction -> filing required
├── Furusato Nozei with six or more municipalities or no one-stop filing -> filing required
├── Year-end adjustment not completed -> filing required
├── Wants to carry forward listed-stock losses -> filing required
└── Otherwise -> usually not required

Non-salary conditions:
├── Business income exists -> filing required
├── Real-estate income exists -> filing required
├── Retirement income without the proper declaration -> filing required
├── Public pension income exceeds JPY 4 million -> filing required
├── Non-pension income exceeds JPY 200,000 -> filing required
├── Capital gains exist -> depends on the category
├── Total income exceeds the basic deduction -> filing required
└── Otherwise -> usually not required
```

### Quick Boundaries to Preserve

| Condition | Income-tax filing | Notes |
|-----------|-------------------|-------|
| One salary source + other income `<= JPY 200,000` | Usually not required | Resident-tax filing may still be required |
| Salary from two or more employers | Required in many cases | Check the subordinate-salary exception |
| Salary income `> JPY 20 million` | Required | No year-end-adjustment shortcut |
| Public pension income `<= JPY 4 million` and other income `<= JPY 200,000` | Usually not required | Resident-tax filing may still be required |
| Business income exists | Required in principle | Sole proprietors normally file |
| Medical-expense deduction or first-year housing-loan deduction | Filing required or beneficial | Refund filing path |

## The 20万円 Rule

### Applies Only If All Conditions Hold

1. Salary income is JPY 20 million or less.
2. Salary is from one employer only, or subordinate salary is within the allowed limit.
3. Year-end adjustment has been completed.

If all three conditions hold, non-salary income of JPY 200,000 or less usually does not require an income-tax return.

### Important Notes

| Point | Meaning |
|-------|---------|
| Resident tax is separate | Even when income-tax filing is unnecessary, resident-tax filing may still be required. |
| Judge by income, not revenue | Use `revenue - expenses = income`. |
| Filing cancels the shortcut | If the user files for medical expenses or another reason, the under-JPY-200,000 side income must also be included. |
| Withholding-account gains can be excluded | Listed-stock gains in withholding accounts are often outside this rule. |
| Crypto gains count | Crypto gains are usually miscellaneous income for this test. |

### Cases Outside the Rule

- Salary income exceeds JPY 20 million.
- The taxpayer is an officer of a closely held company and receives certain related income.
- Disaster-relief special treatment applies.
- Salary is paid by a payer with no withholding obligation.

## Salary Earners with Side Work

```text
Step 1: Confirm annual side-work revenue.
Step 2: Subtract expenses to calculate side-work income.
Step 3: If side-work income is JPY 200,000 or less:
  -> Income-tax filing may be unnecessary, but resident-tax filing may still be required.
Step 4: If side-work income exceeds JPY 200,000:
  -> Filing required.
Step 5: Decide whether the side-work income is business income or miscellaneous income.
```

## Freelancers and Sole Proprietors

```text
General rule: if business income exists, filing is required.

Exception: if taxable income stays within the basic deduction range, income-tax filing may be unnecessary.
Still consider filing when:
- a loss carryforward is needed,
- withholding tax should be refunded, or
- resident-tax filing remains necessary.
```

## Penalties and Relief

### Additional Taxes

| Type | Rate | Trigger |
|------|------|---------|
| `無申告加算税` | 15% (`20%` above JPY 500,000) | Late filing |
| Voluntary late filing | 5% | Filed before a tax-office notice |
| `過少申告加算税` | 10% (`15%` above the higher threshold) | Underreported tax found after filing |
| Voluntary correction | 0% | Corrected before a tax-office notice |
| `重加算税` | 35% (`40%` for no filing) | Concealment or fabrication |

### Delinquency Tax

| Period | Rate (`令和6年`) |
|--------|-----------------|
| From the day after the deadline to two months later | 2.4% per year |
| More than two months late | 8.7% per year |

### Criminal Exposure

| Offense | Statutory penalty |
|---------|-------------------|
| Tax evasion (`所得税法238条`) | Up to 10 years in prison or up to JPY 10 million fine, or both |
| Failure to file (`所得税法241条`) | Up to 1 year in prison or up to JPY 500,000 fine |

### Relief for Voluntary Late Filing

No `無申告加算税` if all of the following hold:

1. The return is filed voluntarily within one month after the deadline.
2. Full payment was completed by the original deadline.
3. No `無申告加算税` or `重加算税` was imposed in the previous five years.

## Refund Filing

### Common Cases

| Situation | Typical taxpayer |
|-----------|------------------|
| Medical-expense deduction after year-end adjustment | Salary earner |
| Furusato Nozei deduction without the one-stop route | Salary earner |
| First-year housing-loan deduction | Home purchaser |
| Mid-year resignation without year-end adjustment | Former employee |
| Excess withholding tax | Freelancer or contractor |

### Deadline

Refund filing can usually be made from January 1 of the following year for five years.

## Pensioners

The simplified no-filing path usually applies only if all of the following are true:

1. Public pension income is JPY 4 million or less.
2. All public pension income was subject to withholding.
3. Non-pension income is JPY 200,000 or less.

> This file is a general decision aid. If facts are unusual or a filing decision materially affects tax treatment, respond as `L3` and recommend the tax office or a tax accountant.
