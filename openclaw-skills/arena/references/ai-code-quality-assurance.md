# AI-Generated Code Quality Assurance

> LLM 生成コードの既知問題パターン、品質リスク統計、検出戦略、レビューベストプラクティス

## 1. AI 生成コードの品質統計（2025-2026）

| 指標 | 値 | 出典 |
|------|---|------|
| セキュリティ欠陥含有率 | **45%** | Veracode 2025 GenAI Code Security Report |
| 人間比バグ発生率 | **1.7 倍** | Sonar 2025 Code Quality Report |
| 重大/メジャー issue 発生率 | **1.3-1.7 倍** | Sonar 2025 |
| セキュリティバグ発生率（パスワード処理、オブジェクト参照） | **1.5-2.0 倍** | Sonar 2025 |
| 過剰 I/O 操作 | **約 8 倍** | Sonar 2025 |
| 並行性・依存性の正確性ミス | **2 倍** | Sonar 2025 |
| ロジックエラー頻度 | **1.75 倍** | Addy Osmani, Code Review in the Age of AI |
| XSS 脆弱性 | **2.74 倍** | Addy Osmani |
| AI 採用 90% 増 → バグ率 | **+9%** | Stack Overflow Blog 2026 |
| AI 採用 → コードレビュー時間 | **+91%** | Stack Overflow Blog 2026 |
| AI 採用 → PR サイズ | **+154%** | Stack Overflow Blog 2026 |

---

## 2. AI 生成コードの 8 大問題カテゴリ

| # | カテゴリ | 説明 | Arena での検出 |
|---|---------|------|---------------|
| **QA-01** | **Silent Failure（静かな失敗）** | 構文エラーやクラッシュを避けつつ、安全チェックを削除したり偽の出力を生成。正常に見えるが結果が不正 | テスト実行 + Acceptance Criteria 照合で検出 |
| **QA-02** | **ロジックエラー** | 条件分岐の誤り、off-by-one、境界条件の見落とし（人間の 1.75 倍） | codex review + テスト結果で Correctness スコアに反映 |
| **QA-03** | **セキュリティ脆弱性** | 入力サニタイゼーション欠如（最多）、XSS、不適切なパスワード処理、安全でないオブジェクト参照 | Safety スコアで評価 · セキュリティクリティカルは Sentinel 連携 |
| **QA-04** | **過剰 I/O** | 不必要なファイル読み書き、API コール、DB クエリ（8 倍） | Performance スコアで評価 · 定量メトリクスで検出 |
| **QA-05** | **並行性バグ** | Race condition、デッドロック、不適切な非同期処理（2 倍） | テスト + codex review の Safety findings |
| **QA-06** | **非推奨 API の使用** | 古いフレームワーク API、deprecated なメソッドの使用 | Build 警告 + codex review で検出 |
| **QA-07** | **過剰な抽象化** | 不要なクラス階層、過度なパターン適用、必要以上のファイル分割 | Simplicity スコアで評価 · コードボリューム比較 |
| **QA-08** | **コードベース不整合** | 既存パターンと異なるスタイル、命名規則の不一致、重複コード生成 | Code Quality スコア · codex review · 手動レビュー |

---

## 3. Arena 固有の品質リスク

### COMPETE モードのリスク

| リスク | 説明 | 軽減策 |
|-------|------|--------|
| **両 variant が同じバグ** | 同じ LLM の弱点で同じロジックエラー | Self-Competition で approach hint を変えて多様性確保 |
| **見た目の品質 ≠ 実品質** | 洗練されたコードが Silent Failure を含む | テスト実行を必須化 · Acceptance Criteria で機能検証 |
| **codex review の過剰訂正** | LLM レビューアが正しいコードを「不適合」と判定 | codex review は補助証拠として使用 · Arena 独自分析を優先 |

### COLLABORATE モードのリスク

| リスク | 説明 | 軽減策 |
|-------|------|--------|
| **インターフェース不整合** | subtask 間で型定義が矛盾 | shared_read で型を共有 · INTEGRATE 時にインターフェースチェック |
| **統合後の新規バグ** | 個別は正常だが統合時に問題発生 | VERIFY フェーズで統合テスト必須 |
| **セキュリティ境界の漏れ** | 各 subtask は安全だが全体で脆弱性 | 統合後に Sentinel レビュー推奨 |

---

## 4. 品質検出戦略

### 多層防御モデル

```
Layer 1: 自動検出（機械的）
  ├── Scope Validation: git diff で forbidden files チェック
  ├── Build Verification: コンパイル/ビルド成功
  ├── Test Execution: 既存テスト + 新規テスト
  └── Static Analysis: codex review（Code Quality + Safety）

Layer 2: 定量メトリクス（客観的）
  ├── Code Volume: 行数、ファイル数（Simplicity 指標）
  ├── Exported Symbols: API サーフェス面積
  ├── Test Coverage Delta: カバレッジ増減
  └── Build Time: パフォーマンス間接指標

Layer 3: 比較分析（Arena 固有）
  ├── Variant 間差分: git diff で実装の違いを可視化
  ├── Function-Level Diff: 論理単位での変更比較
  └── Cross-Variant Bug Detection: 片方にのみ存在するバグの発見

Layer 4: 人間レビュー（高信号）
  ├── アーキテクチャ適合性: ロードマップとの整合
  ├── ビジネスロジック正確性: ドメイン知識必要
  └── セキュリティ脅威モデリング: 認証・決済・秘密情報
```

### AI レビューの限界

```
AI codex review が見逃しやすいもの:
  - 状態・アイデンティティ・順序に依存するバグ
  - エンドツーエンドフローでのみ顕在化する問題
  - アーキテクチャ的な不適合
  - 既存コードの意図的な重複（AI は重複を生成しがち）
  - 長期メンテナビリティの問題

AI codex review が過剰検出しやすいもの:
  - 正しいが珍しいパターン → 「不適合」と誤判定
  - 文脈上安全だが一般的にリスクのあるパターン
  - フレームワーク固有のイディオム

対策:
  - codex review は「補助証拠」として扱い、Arena の独自分析を優先
  - Safety/Security 関連の findings は Sentinel に委譲
  - 重大な判断は人間レビューをゲートに
```

---

## 5. variant 比較による品質向上

### COMPETE の品質優位性

```
単一エンジン生成 vs COMPETE の差:

  単一エンジン:
    - 1 つの実装のみ → バグの検出が受動的
    - LLM の弱点がそのまま出力に反映

  COMPETE (2+ variant):
    - 複数実装の比較 → バグの能動的発見
    - variant A にのみ存在するバグ → variant B との差分で検出可能
    - variant A のロジックエラー → variant B の正しい実装が比較対象に
    - 異なるアプローチ → 多様なエッジケースカバレッジ

品質向上メカニズム:
  1. Cross-Variant Diff: 実装の違いがバグ候補を示唆
  2. Score Gap Analysis: 大きなスコア差 → 弱い variant のバグが明確
  3. Hybrid Selection: 各 variant の長所を組み合わせ
```

### AI レビュー × 人間レビューのハイブリッド

```
推奨ワークフロー（Addy Osmani の "PR Contract" 適用）:

  1. Intent Clarity: 変更の意図を 1-2 文で説明
  2. Proof of Functionality: テスト結果 + 手動検証ステップ
  3. Risk Assessment: AI 生成部分を特定 · セキュリティクリティカル箇所をマーク
  4. Review Focus: 人間レビューの注力ポイントを 1-2 個指定

Arena 適用:
  - COMPETE: Comparison Report に Intent + Risk を含める
  - COLLABORATE: Integration Report に各 subtask の AI 生成状況を記載
  - 両方: Guardian ハンドオフ時に AI 生成コードのマーキング推奨
```

---

## 6. Arena との連携

```
Arena での活用:
  1. REVIEW フェーズで QA-01〜08 の検出を体系化
  2. EVALUATE で多層防御モデルの各レイヤーを適用
  3. COMPETE の Cross-Variant Diff で能動的バグ検出
  4. Guardian ハンドオフ時に AI 生成コードの品質リスク情報を付加

品質ゲート:
  - Silent Failure 疑い（テスト PASS だが Acceptance Criteria 未達）→ 手動検証を強制
  - セキュリティクリティカルコード → Sentinel 連携を必須化
  - codex review の過剰訂正 → Arena 独自分析で上書き可能（根拠必須）
  - 全 variant の Correctness ≤ 2 → spec 見直しを推奨（コード問題ではなく spec 問題の可能性）
```

**Source:** [IEEE Spectrum: AI Coding Degrades](https://spectrum.ieee.org/ai-coding-degrades) · [Stack Overflow: Bugs and AI Coding Agents](https://stackoverflow.blog/2026/01/28/are-bugs-and-incidents-inevitable-with-ai-coding-agents) · [Sonar: Poor Code Quality in AI Codebases](https://www.sonarsource.com/blog/the-inevitable-rise-of-poor-code-quality-in-ai-accelerated-codebases/) · [Addy Osmani: Code Review in the Age of AI](https://addyo.substack.com/p/code-review-in-the-age-of-ai) · [GroweXX: AI Code Security Crisis 2026](https://www.growexx.com/blog/ai-code-security-crisis-2026-cto-guide/)
