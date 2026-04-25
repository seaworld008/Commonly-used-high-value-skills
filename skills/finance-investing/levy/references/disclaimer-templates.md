# Disclaimer Templates

Purpose: Read this when you need the mandatory disclaimer text, the `L1`-`L4` guardrail level, or escalation wording.

## Standard Disclaimer

Append this to every response:

```text
⚠️ 本回答は一般的な税法解説であり、個別具体的な税務判断・税務相談に該当するものではありません。
実際の申告にあたっては、対象年度の最新の税法・通達を確認し、必要に応じて税理士にご相談ください。
```

## Calculation Disclaimer

Use this for any estimate, simulation, or tax preview:

```text
⚠️ 本計算は提供された情報に基づく概算です。
・対象年度: [年度]
・前提条件: [使用した前提をリスト]
正確な税額は、全ての所得・控除を反映した確定申告書の作成が必要です。
```

## Tax-Law Update Disclaimer

Use this when the answer depends on year-sensitive rules:

```text
⚠️ 本情報は[年度]時点の税法に基づいています。
税制改正により要件・税率・控除額等が変更される可能性があります。
最新情報は国税庁サイト（https://www.nta.go.jp）を確認してください。
```

## Special-Income Disclaimer

Use this for crypto, foreign income, stock options, or similar cases:

```text
⚠️ [暗号資産取引/海外所得/ストックオプション等]の税務処理は複雑であり、
取引の態様・時期・金額等により取扱いが異なります。
専門の税理士への相談を強く推奨します。
```

## Guardrail Levels

| Level | Response policy | Typical examples |
|-------|-----------------|------------------|
| `L1` | Answer directly | Income-tax basics, deduction categories, filing flow |
| `L2` | Answer with disclaimer | Salary-plus-side-business estimate, deduction calculations |
| `L3` | General guidance only, then recommend a tax accountant | Income-type judgment, complex eligibility calls, amendments |
| `L4` | Refuse and point to expert help | Tax evasion, fabricated expenses, audit avoidance |

## Never Include

| Prohibited content | Why |
|--------------------|-----|
| `「確実に〜できます」`, `「必ず〜です」` | Guarantee language can become de facto tax judgment |
| `「申告しなくてもバレません」` | Implies tax evasion |
| Definitive individualized tax judgment | Risks violating tax-accountant practice limits |
| My Number or bank-account retention | Sensitive personal data |
| Instructions for fabricated expenses | Assists tax evasion |
| Instructions for avoiding a tax audit | Non-compliant and unsafe |

## Recommend a Tax Accountant When

- Annual revenue exceeds JPY 10 million and consumption tax becomes relevant.
- Incorporation is under consideration.
- Crypto trading volume is large.
- Foreign transactions or overseas residency history are involved.
- Inheritance or gift tax intersects with income tax.
- The user has received a tax-audit notice.
- The request concerns an amended return or a correction claim.

## Escalation Template

```text
この質問は個別具体的な税務判断に該当するため、一般的な解説にとどめます。

正確な判断には以下をおすすめします:
1. 税理士への相談（日本税理士会連合会: https://www.nichizeiren.or.jp）
2. 税務署の無料相談（確定申告期間中）
3. 国税庁電話相談センター（最寄りの税務署に電話 → 自動案内で「1」）
```
