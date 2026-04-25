# Interaction Triggers

Purpose: Read this when a user request hits a decision boundary and you need the canonical trigger, default action, keyword heuristic, or YAML interaction template.

## Contents

- [Trigger list](#trigger-list)
- [YAML templates](#yaml-templates)
- [Keyword heuristics](#keyword-heuristics)

## Trigger List

| Trigger | Condition | Default action |
|---------|-----------|----------------|
| `FISCAL_YEAR_UNKNOWN` | The target filing year is not stated | Apply the latest filing year by default |
| `INCOME_TYPE_AMBIGUOUS` | Business income vs miscellaneous income is unclear | Show the business-income checklist |
| `SPECIAL_INCOME` | Crypto, foreign income, stock options, large property sales, or similar cases | Recommend a tax accountant and stay at general guidance |
| `CONSUMPTION_TAX` | Revenue exceeds JPY 10 million or invoice registration is relevant | Show the taxable-business decision flow |
| `AMENDMENT_REQUEST` | The user asks about amended returns, correction claims, or late filing | Treat as `L3` and recommend a tax accountant |
| `BLUE_FILING_ELIGIBILITY` | Blue filing approval status is unclear | Confirm the approval status |
| `SALARY_PLUS_BUSINESS` | Salary income and business income must be filed together | Switch to the combined-filing guide |
| `ACCRUAL_BASIS_CHECK` | The user asks about a transaction crossing the year-end | Reconfirm accrual-basis timing |
| `DEDUCTION_OVERLAP_CHECK` | Duplicate deduction input is likely | Run the overlap checklist |

## YAML Templates

### FISCAL_YEAR_UNKNOWN

```yaml
INTERACTION_TRIGGER:
  type: FISCAL_YEAR_UNKNOWN
  condition: "対象年度が明示されていない"
  question: "どの年度の確定申告についてお聞きですか？"
  options:
    - "直近の申告年度 — 直近の法定申告期限がある年度(Recommended)"
    - "1つ前の申告年度"
    - "過年度 — 期限後申告・還付申告"
    - "Other（詳細を教えてください）"
  context:
    current_date: "[現在日付]"
    filing_deadline: "対象年度の翌年3月15日"
  default: "直近の申告年度"
```

### INCOME_TYPE_AMBIGUOUS

```yaml
INTERACTION_TRIGGER:
  type: INCOME_TYPE_AMBIGUOUS
  condition: "副業収入の所得区分（事業所得 vs 雑所得）が判定困難"
  question: "副業の所得区分を判定するため、以下のどれに該当しますか？"
  options:
    - "開業届提出済み・反復継続的な収入・独立した事業として運営 → 事業所得"
    - "会社員の副業・年間収入300万円以下・開業届未提出 → 雑所得(Recommended)"
    - "判断が難しい — 詳細ヒアリングを希望"
    - "Other（詳細を教えてください）"
  context:
    revenue_amount: "[年間収入額]"
    has_opening_notification: "[開業届の有無]"
    business_continuity: "[反復継続性]"
  default: "雑所得"
  reference: "所得税基本通達35-2、国税庁「雑所得の範囲の明確化」"
```

### SPECIAL_INCOME

```yaml
INTERACTION_TRIGGER:
  type: SPECIAL_INCOME
  condition: "暗号資産・海外所得・ストックオプション・不動産売却等の特殊所得を検出"
  question: "特殊な所得が含まれています。どのように対応しますか？"
  options:
    - "一般的な解説と計算の大枠を提示（免責事項付き）(Recommended)"
    - "税理士への相談を推奨（紹介基準を提示）"
    - "該当所得を除外し、他の所得のみ計算"
    - "Other（詳細を教えてください）"
  context:
    special_income_type: "[検出した特殊所得の種類]"
    estimated_amount: "[概算金額]"
  default: "一般的な解説と計算の大枠を提示（免責事項付き）"
  guardrail: "references/disclaimer-templates.md L3テンプレートを適用"
```

### CONSUMPTION_TAX

```yaml
INTERACTION_TRIGGER:
  type: CONSUMPTION_TAX
  condition: "年間売上が1,000万円超、またはインボイス登録に関する質問"
  question: "消費税に関する判断が必要です。現在の状況を教えてください。"
  options:
    - "免税事業者（年間売上1,000万円以下）— インボイス登録を検討中"
    - "課税事業者 — 簡易課税を選択済み(Recommended)"
    - "課税事業者 — 本則課税"
    - "Other（詳細を教えてください）"
  context:
    annual_revenue: "[年間売上]"
    invoice_registration: "[インボイス登録状況]"
    tax_method: "[課税方式]"
  default: "課税事業者 — 簡易課税を選択済み"
  reference: "消費税法第9条、インボイス制度（適格請求書等保存方式）"
```

### AMENDMENT_REQUEST

```yaml
INTERACTION_TRIGGER:
  type: AMENDMENT_REQUEST
  condition: "修正申告・更正の請求・期限後申告に関する質問"
  question: "修正申告・更正の請求は専門的な判断が必要です。どう進めますか？"
  options:
    - "税理士への相談を推奨（一般的な手続きフローのみ案内）(Recommended)"
    - "一般的な制度解説のみ提示（免責事項付き）"
    - "修正内容が単純なため手続きガイドを希望"
    - "Other（詳細を教えてください）"
  context:
    amendment_type: "[修正申告 / 更正の請求 / 期限後申告]"
    original_filing_date: "[当初申告日]"
    reason: "[修正理由]"
  default: "税理士への相談を推奨"
  guardrail: "references/disclaimer-templates.md L3テンプレートを適用"
```

### BLUE_FILING_ELIGIBILITY

```yaml
INTERACTION_TRIGGER:
  type: BLUE_FILING_ELIGIBILITY
  condition: "青色申告の適用可否が不明"
  question: "青色申告承認申請書は提出済みですか？"
  options:
    - "提出済み — 65万円控除を適用(Recommended)"
    - "未提出 — 今年度から申請したい（期限・手続きを案内）"
    - "不明 — 確認方法を知りたい"
    - "Other（詳細を教えてください）"
  context:
    business_start_date: "[事業開始日]"
    filing_history: "[過去の申告実績]"
  default: "提出済み — 65万円控除を適用"
  reference: "所得税法第143条〜第151条"
```

### SALARY_PLUS_BUSINESS

```yaml
INTERACTION_TRIGGER:
  type: SALARY_PLUS_BUSINESS
  condition: "給与所得と事業所得の両方がある場合の合算申告"
  question: "会社員+副業の確定申告ですね。以下の状況を教えてください。"
  options:
    - "会社員+副業（青色申告）— 合算申告ガイドを表示(Recommended)"
    - "会社員+副業（白色申告）— 基本的な合算申告ガイド"
    - "副業のみ — 事業所得の申告ガイド"
    - "Other（詳細を教えてください）"
  context:
    salary_income: "[給与収入]"
    business_income: "[事業収入]"
    blue_filing: "[青色申告承認の有無]"
  default: "会社員+副業（青色申告）"
  reference: "references/salary-plus-side-business.md"
```

### ACCRUAL_BASIS_CHECK

```yaml
INTERACTION_TRIGGER:
  type: ACCRUAL_BASIS_CHECK
  condition: "年末年始をまたぐ取引があり、計上時期の確認が必要"
  question: "年度をまたぐ取引の計上時期を確認します。"
  options:
    - "役務提供日基準で計上済み — 発生主義(Recommended)"
    - "入金日で計上している — 現金主義（確認が必要）"
    - "年末の売掛金処理を確認したい"
    - "Other（詳細を教えてください）"
  context:
    fiscal_year: "[対象年度]"
    year_end_receivables: "[年末売掛金の有無]"
  default: "役務提供日基準で計上済み"
  reference: "所得税法第36条（収入金額の権利確定主義）"
```

### DEDUCTION_OVERLAP_CHECK

```yaml
INTERACTION_TRIGGER:
  type: DEDUCTION_OVERLAP_CHECK
  condition: "源泉徴収票で処理済みの控除と確定申告入力の重複リスク検出"
  question: "控除の重複入力を防止するため確認します。"
  options:
    - "源泉徴収票の控除内容を確認して重複チェックする(Recommended)"
    - "控除の重複回避チェックリストを表示"
    - "源泉徴収票の読み方を教えてほしい"
    - "Other（詳細を教えてください）"
  context:
    has_withholding_slip: "[源泉徴収票の有無]"
    controls_in_slip: "[源泉徴収票で処理済みの控除]"
  default: "源泉徴収票の控除内容を確認して重複チェックする"
  reference: "references/salary-plus-side-business.md 控除の重複回避チェックリスト"
```

## Keyword Heuristics

Keep these Japanese keyword cues unchanged because they are part of the routing behavior.

| Detected keyword | Trigger |
|------------------|---------|
| `「何年」`, `「いつの」`, `「年度」` with no clear year | `FISCAL_YEAR_UNKNOWN` |
| `「副業」`, `「事業か雑か」`, `「開業届」`, `「300万円」` | `INCOME_TYPE_AMBIGUOUS` |
| `「暗号資産」`, `「仮想通貨」`, `「海外」`, `「ストックオプション」`, `「不動産売却」` | `SPECIAL_INCOME` |
| `「消費税」`, `「インボイス」`, `「1000万円」`, `「課税事業者」`, `「簡易課税」` | `CONSUMPTION_TAX` |
| `「修正申告」`, `「更正」`, `「間違えた」`, `「やり直し」`, `「期限後」` | `AMENDMENT_REQUEST` |
| `「青色申告」`, `「65万円控除」`, `「承認申請」` | `BLUE_FILING_ELIGIBILITY` |
| `「会社員」`, `「給与+副業」`, `「サラリーマン」`, `「合算」` | `SALARY_PLUS_BUSINESS` |
| `「売掛金」`, `「発生主義」`, `「年末」`, `「12月分」`, `「計上時期」` | `ACCRUAL_BASIS_CHECK` |
| `「控除の重複」`, `「源泉徴収票」`, `「二重」`, `「入力済み」` | `DEDUCTION_OVERLAP_CHECK` |
