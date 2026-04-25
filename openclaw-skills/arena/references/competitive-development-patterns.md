# Competitive & Collaborative Development Patterns

> マルチエージェント協調の設計パターン、Arena COMPETE/COLLABORATE への適用、品質最大化戦略

## 1. マルチエージェント設計パターン

### 8 つの協調パターン

| # | パターン | 概要 | Arena 対応 |
|---|---------|------|-----------|
| **CP-01** | **Sequential Pipeline** | 直列実行、前の出力が次の入力 | Solo Mode の sequential variant 実行 |
| **CP-02** | **Coordinator/Dispatcher** | 中央オーケストレーターが専門エージェントに振り分け | Arena リーダーがエンジン選択・タスク分配 |
| **CP-03** | **Parallel Fan-Out/Gather** | 並列実行 → 結果集約 | Team Mode の parallel variant 生成 |
| **CP-04** | **Hierarchical Decomposition** | 高次タスクを分解して委譲 | COLLABORATE の DECOMPOSE フェーズ |
| **CP-05** | **Generator-Critic** | 生成 → 批評 → 条件ループ | EXECUTE → REVIEW → REFINE サイクル |
| **CP-06** | **Iterative Refinement** | 生成 → 批評 → 改善の反復 | REFINE フェーズ（max 2 iteration） |
| **CP-07** | **Human-in-the-Loop** | 高リスク操作で人間承認 | 3+ variant 確認 · Team Mode 確認 · セキュリティレビュー |
| **CP-08** | **Composite** | 複数パターンの組み合わせ | Arena の完全ワークフロー（複数パターンの合成） |

---

## 2. Arena パラダイムと設計パターンの対応

### COMPETE = Fan-Out/Gather + Generator-Critic

```
COMPETE のパターン分解:

  Fan-Out（並列生成）:
    ┌── codex variant ──┐
    │                    │
    Spec ──┤                    ├── EVALUATE → ADOPT
    │                    │
    └── gemini variant ──┘

  + Generator-Critic（品質ゲート）:
    EXECUTE（Generator）→ REVIEW（Critic）→ EVALUATE → [REFINE] → ADOPT

  Team Mode では Fan-Out が物理的な並列実行
  Solo Mode では Fan-Out が論理的な順次実行
```

### COLLABORATE = Hierarchical Decomposition + Pipeline

```
COLLABORATE のパターン分解:

  Hierarchical Decomposition（タスク分割）:
    Full Spec
    ├── Subtask A (codex) → arena/task-a
    └── Subtask B (gemini) → arena/task-b

  + Pipeline（依存順統合）:
    Subtask A → INTEGRATE → Subtask B → VERIFY

  非重複スコープが Decomposition の品質を決定
  Integration Order が Pipeline の正確性を決定
```

---

## 3. 競争開発の品質最大化戦略

### Variant 多様性の設計

```
多様性が高いほど:
  - より多くの設計空間を探索
  - バグの Cross-Variant Detection が効果的
  - 最善のアプローチを発見する確率が上昇

多様性を生む 4 軸:

  1. エンジン多様性: codex vs gemini（最大の多様性）
  2. アプローチ多様性: iterative vs functional vs OOP
  3. モデル多様性: o4-mini vs o3（同一エンジン内）
  4. プロンプト多様性: concise vs detailed

Multi-Variant Matrix（最大多様性）:
  ┌──────────┬───────────┬───────────┐
  │          │ iterative │ functional│
  ├──────────┼───────────┼───────────┤
  │ codex    │ variant-1 │ variant-2 │
  │ gemini   │ variant-3 │ variant-4 │
  └──────────┴───────────┴───────────┘
  → 4 variant で engine × approach の完全マトリクス

注意: variant 数とコストはトレードオフ
  2 variant: 低コスト、基本比較（Quick/Solo デフォルト）
  3 variant: 中コスト、良好な多様性（Solo 推奨上限）
  4+ variant: 高コスト、最大多様性（Team Mode + 確認必須）
```

### Hybrid Selection（ハイブリッド採用）

```
通常: Winner を 1 つ選択
ハイブリッド: 各 variant の長所を組み合わせ

適用条件:
  - スコア差 ≤ 0.2（明確な勝者なし）
  - 各 variant に異なる強みがある
  - ファイルスコープが重複していない

手順:
  1. Criterion ごとに最高スコア variant を特定
  2. ファイル単位で最善の実装を選択
  3. git cherry-pick / 手動 merge で統合
  4. 統合後に VERIFY を実行

リスク:
  - 統合の複雑性が増す
  - 一貫性が損なわれる可能性
  → スコア差が大きい場合は単一 winner を推奨
```

---

## 4. 協力開発の統合パターン

### Decomposition の 5 原則

| # | 原則 | 説明 | 違反時のリスク |
|---|------|------|--------------|
| **1** | **非重複ファイルスコープ** | 各ファイルは 1 subtask のみに所属 | Merge conflict · 出力の上書き |
| **2** | **共有読み取り専用** | 型定義・インターフェースは shared_read | 型の不整合（MO-02） |
| **3** | **依存順序の明示** | integration_order で merge 順を定義 | 統合後のビルド失敗 |
| **4** | **エンジン強度整合** | subtask 特性とエンジン強みを合致 | 低品質出力（Engine-Subtask Mismatch） |
| **5** | **最小 subtask 数** | 2-4 subtask を推奨（5+ は確認必須） | コスト爆発 · 統合複雑性 |

### 統合戦略の選択

```
Clean Merge（デフォルト）:
  - 非重複スコープなら conflict なし
  - git merge を依存順に実行
  - 最もシンプルで安全

Cherry-Pick Merge:
  - subtask の一部コミットのみ統合
  - 部分的な失敗復旧に有効
  - 手動操作が必要

Manual Integration:
  - インターフェース不整合時
  - Arena リーダーが Edit で解決
  - 最も柔軟だが最もリスキー

判定:
  Conflict なし → Clean Merge
  Conflict あり + 局所的 → Cherry-Pick
  Conflict あり + 構造的 → Manual Integration
```

---

## 5. パラダイム選択の最適化

### 判定フローチャート

```
タスクの性質は？
  │
  ├─ 複数の有効なアプローチあり → COMPETE
  │   ├─ ≤ 3 files, ≤ 50 lines → Quick
  │   ├─ 2 variant → Solo
  │   └─ 3+ variant → Team（確認必須）
  │
  ├─ 自然に分割可能 → COLLABORATE
  │   ├─ 2 subtask, ≤ 4 files → Quick Collaborate
  │   ├─ 2 subtask → Solo
  │   └─ 3+ subtask → Team（確認必須）
  │
  ├─ 不確実性が高い → COMPETE（アプローチ探索）
  │
  ├─ 各部分に異なるエンジン強みが合致 → COLLABORATE
  │
  └─ 判断不能 → デフォルト COMPETE（比較が情報量多い）
```

### COMPETE vs COLLABORATE の実績ベース学習

```
CALIBRATE で蓄積するデータ:

  Task Type × Paradigm の勝率マトリクス:
    │          │ COMPETE │ COLLABORATE │
    │ feature  │  70%    │    30%      │
    │ bugfix   │  90%    │    10%      │
    │ refactor │  60%    │    40%      │
    │ migration│  30%    │    70%      │

  → migration は COLLABORATE 優位（複数ファイルの並行変更）
  → bugfix は COMPETE 優位（正解が 1 つ、比較で品質確保）
  → feature/refactor はケースバイケース
```

---

## 6. コスト・品質トレードオフ

### モード別コスト効率

| モード | Variant 数 | 並列性 | コスト | 品質 | 推奨場面 |
|--------|-----------|--------|--------|------|---------|
| **Quick** | 2 | なし | 最低 | 基本 | ≤ 3 files の小変更 |
| **Solo** | 2 | なし | 低 | 良好 | 標準的な機能実装 |
| **Solo 3-variant** | 3 | なし | 中 | 高 | 品質が重要な実装 |
| **Team 2** | 2 | あり | 中 | 良好 + 高速 | 時間制約あり |
| **Team 3+** | 3+ | あり | 高 | 最高 | 重要機能 · セキュリティ |

### Auto-Escalation 判定

```
Quick → Solo にエスカレーション:
  - merge conflict 発生
  - integrated score < 3.0
  - 出力が 40 lines 超

Solo → Team にエスカレーション:
  - 3+ variant が必要と判断
  - 時間制約で並列化が必要
  - ユーザーの明示的な要求

エスカレーション時は常にユーザーに通知
```

---

## 7. Arena との連携

```
Arena での活用:
  1. パラダイム選択で判定フローチャートを適用
  2. COMPETE で Variant 多様性の 4 軸を活用
  3. COLLABORATE で Decomposition の 5 原則を遵守
  4. CALIBRATE で実績ベースの学習を蓄積

品質ゲート:
  - Decomposition で重複スコープ → COLLABORATE 開始前にブロック
  - Variant 多様性が低い（同一アプローチ）→ approach hint 追加を推奨
  - パラダイム選択の根拠なし → 判定フローチャートの適用を要求
  - Hybrid Selection でスコア差 > 0.5 → 単一 winner 推奨
```

**Source:** [Google ADK Multi-Agent Patterns](https://developers.googleblog.com/developers-guide-to-multi-agent-patterns-in-adk/) · [GitHub Blog: Multi-Agent Workflows](https://github.blog/ai-and-ml/generative-ai/multi-agent-workflows-often-fail-heres-how-to-engineer-ones-that-dont/) · [AWS: Multi-Agent Collaboration Patterns](https://aws.amazon.com/blogs/machine-learning/multi-agent-collaboration-patterns-with-strands-agents-and-amazon-nova/) · [Azure: AI Agent Design Patterns](https://learn.microsoft.com/en-us/azure/architecture/ai-ml/guide/ai-agent-design-patterns)
