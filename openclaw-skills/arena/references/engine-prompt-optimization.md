# Engine Prompt Optimization

> コード生成プロンプトの最新最適化テクニック、構造化フレームワーク、アンチパターン、反復改善戦略

## 1. プロンプト構造化フレームワーク

### GOLDE フレームワーク（コード生成特化）

| 要素 | 説明 | Arena 適用 |
|------|------|-----------|
| **G**oal | 目的と成功基準 | Specification セクション |
| **O**utput | 出力形式・ファイル構造 | Allowed Files リスト |
| **L**imits | スコープ・制約・禁止事項 | Forbidden Files + Constraints |
| **D**ata | コンテキスト・例・参照 | Codebase Context (gemini) |
| **E**valuation | 受入基準・検証方法 | Success Criteria |

### Role-Task-Constraints パターン

```
効果的なエンジンプロンプトの 3 層構造:

Layer 1 — Role（役割設定）
  codex: 不要（コード生成に特化しているため）
  gemini: 有効（"Act as a senior TypeScript engineer" で品質向上）

Layer 2 — Task（タスク定義）
  両エンジン共通: 具体的・命令的な実装指示
  Bad:  "認証機能を改善して"
  Good: "verifyToken(token: string): Promise<UserPayload> を実装。
         jsonwebtoken を使用。期限切れ・不正形式・有効なトークンを処理"

Layer 3 — Constraints（制約）
  両エンジン共通: 行動の境界を明示
  - Allowed Files / Forbidden Files
  - "DO NOT" 制約の明示
  - 受入基準のリスト化
```

---

## 2. エンジン別プロンプト最適化

### codex exec 最適化原則

| 原則 | 詳細 | 効果 |
|------|------|------|
| **簡潔優先** | 短く明確な指示。背景説明を最小化 | 解釈ミス削減 · 実行速度向上 |
| **制約先行** | Allowed/Forbidden Files をプロンプト上部に配置 | スコープ違反率の低下 |
| **パス明示** | ファイルパスを正確に指定 | 意図しないファイル生成の防止 |
| **命令形** | "Create function X that does Y" > "Consider implementing..." | 出力の具体性向上 |
| **導入コード** | `import` や `SELECT` のリードワードで出力パターンを誘導 | 正しいフォーマットの誘導 |

### gemini 最適化原則

| 原則 | 詳細 | 効果 |
|------|------|------|
| **コンテキスト豊富** | ビジネス背景・技術スタック・既存パターンを含める | アーキテクチャ適合性向上 |
| **参照ファイル提示** | 関連ファイル（read-only）をリストアップ | 既存コード規約への適合 |
| **パターン記述** | 既存のコードパターンを説明 | 一貫性のある出力 |
| **代替案要求** | "複数アプローチを検討してから実装" | 創造的解決策の発見 |
| **Role 設定** | "Act as a seasoned TypeScript expert" | 出力品質の全般的向上 |

---

## 3. プロンプトアンチパターン

### コード生成 10 大アンチパターン

| # | アンチパターン | 問題 | 修正 |
|---|-------------|------|------|
| **PE-01** | **曖昧クエリ** | "なぜ動かない？" → 一般的な推測 | エラーメッセージ + 入力 + 期待値を含める |
| **PE-02** | **過負荷プロンプト** | 5 バグ修正 + 3 機能追加 + 最適化を 1 プロンプトで | 単一論理変更（Single Logical Change）ずつ |
| **PE-03** | **成功基準なし** | "速くして" → 何が「速い」か不明 | "O(n log n) で 10k アイテムのソートを最適化" |
| **PE-04** | **コンテキスト欠如** | コードだけ渡して指示なし | 言語・FW・エラー・期待動作を含める |
| **PE-05** | **コピペプロンプト** | 前セッションのプロンプトを更新せず再利用 | 毎回 Scope Lock を再導出 |
| **PE-06** | **不一致な参照** | "上のコード" → LLM のアテンション外 | コードを再引用して明示 |
| **PE-07** | **Approach Hint 欠如** | Self-Competition で variant が類似 | 各 variant に異なるアプローチ指示 |
| **PE-08** | **制約の後付け** | Spec 後に "あ、package.json は触らないで" | 制約をプロンプト構造に組み込む（先行配置） |
| **PE-09** | **例なし仕様** | "価格フォーマットして" → 通貨・桁数が不明 | "formatPrice(2.5) → '$2.50'" の I/O 例を含める |
| **PE-10** | **スタイル未指定** | エンジンが既存コードと異なるスタイルで生成 | 命名規則・フレームワークバージョン・パターンを指定 |

---

## 4. 高度なプロンプト技法

### Documentation-Driven Prompting

```
手順:
  1. 関数の docstring / JSDoc を先に書く
  2. I/O 例を含める
  3. エンジンに「この仕様に合致する実装」を要求

効果:
  - 仕様と実装の乖離を防止
  - テスト可能な受入基準が自然に生成される
  - Arena の Acceptance Criteria と直結
```

### Edge Case Prompting

```
手順:
  1. 基本実装を生成
  2. "このコードで処理すべきエッジケースは？" と質問
  3. LLM が特定したエッジケースを Success Criteria に追加
  4. エッジケース対応を含む改善版を生成

Arena 適用:
  - REFINE フェーズで weakness_list にエッジケースを含める
  - COMPETE で variant 間のエッジケースカバレッジを比較
```

### Incremental Complexity（漸進的複雑化）

```
Step 1: 最小実装（ハッピーパスのみ）
Step 2: エラーハンドリング追加
Step 3: エッジケース対応
Step 4: パフォーマンス最適化

各ステップで検証 → Arena の REFINE サイクルと同期

Anti-pattern: 全要件を 1 プロンプトで → 過負荷（PE-02）
Best practice: 段階的に要件を追加 → 各段階で品質確認
```

### Parallel Alternative Generation

```
同一仕様に異なるアプローチ指示:
  Prompt A: "関数型プログラミングスタイルで実装"
  Prompt B: "オブジェクト指向で実装"
  Prompt C: "最小限の抽象化で実装"

→ Arena の COMPETE パラダイムそのもの
→ Self-Competition の approach hint に直接活用
```

---

## 5. プロンプトテンプレート改善

### 改善版 Spec テンプレート

```
## Specification
{spec_content}

## Examples (I/O)
Input: {sample_input}
Expected: {expected_output}

## Allowed Files
{allowed_files_list}

## Forbidden Files
{forbidden_files_list}

## Constraints
- ONLY modify files in Allowed Files
- DO NOT modify dependencies
- Follow existing code patterns: {pattern_description}
- Language/Framework: {tech_stack}
- Naming convention: {convention}

## Edge Cases to Handle
- {edge_case_1}
- {edge_case_2}

## Success Criteria
1. {criterion_1}
2. {criterion_2}
3. All existing tests pass
4. Build succeeds
```

### REFINE プロンプト改善

```
Re-implement with targeted improvements.

## Original Specification
{original_spec}

## Previous Attempt Analysis
Score: {total}/5.0
Weaknesses:
{weakness_list}

## Improvement Directives
Focus on:
{directives}

## What Worked (preserve)
{strengths}

## Specific Examples of Issues Found
{issue_1}: Line {N} — {description}
{issue_2}: Line {N} — {description}

## Edge Cases Not Covered
{missing_edge_cases}

## Same Constraints Apply
{constraints}
```

---

## 6. Arena との連携

```
Arena での活用:
  1. SPEC フェーズで GOLDE フレームワークを適用
  2. SCOPE LOCK で PE-01〜10 のチェックリスト検証
  3. Self-Competition で Parallel Alternative Generation を活用
  4. REFINE で Edge Case Prompting を組み込み
  5. エンジン別最適化原則で codex/gemini プロンプトを差別化

品質ゲート:
  - Examples (I/O) 未記載 → 警告（PE-09 防止）
  - Constraints がプロンプト末尾 → 先行配置を推奨（PE-08 防止）
  - 単一プロンプトで複数機能 → 分割を要求（PE-02 防止）
  - 技術スタック未記載 → codex はパス、gemini は必須追加（PE-04 防止）
```

**Source:** [Addy Osmani: Prompt Engineering Playbook for Programmers](https://addyo.substack.com/p/the-prompt-engineering-playbook-for) · [OpenAI: Prompt Engineering Guide](https://platform.openai.com/docs/guides/prompt-engineering) · [CodeSignal: Prompt Engineering Best Practices 2025](https://codesignal.com/blog/prompt-engineering-best-practices-2025/) · [DigitalOcean: Prompt Engineering Best Practices](https://www.digitalocean.com/resources/articles/prompt-engineering-best-practices)
