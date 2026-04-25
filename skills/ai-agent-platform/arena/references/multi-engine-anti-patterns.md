# Multi-Engine Orchestration Anti-Patterns

> 複数 AI エンジン協調の落とし穴、失敗モード、信頼性確保のベストプラクティス

## 1. オーケストレーション 10 大アンチパターン

| # | アンチパターン | 症状 | Arena での影響 | 対策 |
|---|-------------|------|---------------|------|
| **MO-01** | **暗黙の状態仮定** | エンジン間で状態・順序・バリデーションの前提がずれる | COLLABORATE で subtask A の出力を subtask B が前提にするが型が不一致 | 明示的インターフェース定義 · shared_read で型を先に合意 |
| **MO-02** | **データ形式ドリフト** | エンジン間でフィールド名・型・フォーマットが微妙にずれる | codex が `userId` を使い gemini が `user_id` を使う → 統合時にランタイムエラー | Scope Lock で型定義ファイルを shared_read に含め、命名規則を明記 |
| **MO-03** | **曖昧な仕様渡し** | 「分析して適切に対応」のような指示 → 各エンジンが異なる解釈 | COMPETE で variant 間の比較が無意味に（異なる機能を実装） | Spec フェーズで受入基準を必ず列挙 · Success Criteria 必須 |
| **MO-04** | **スコープ侵犯の放置** | エンジンが forbidden_files を変更しても検出・修復しない | package.json が変更されてビルド環境が壊れる | Post-Execution Scope Validation を必ず実行 · revert 自動化 |
| **MO-05** | **単一障害点のオーケストレーター** | Arena リーダーがボトルネック化 → 全 variant/subtask がブロック | Team Mode で worktree 準備が遅れ全 subagent が待機 | 準備作業（branch/worktree）を全て事前に完了してから spawn |
| **MO-06** | **コスト認識の欠如** | variant 数・プロンプトサイズの制御なしにエンジンを呼び出す | 4+ variant × 大規模プロンプト → API コスト爆発 | Cost Estimate 表示 · 3+ variant 時は確認必須 |
| **MO-07** | **評価バイアス** | 最後に見た variant を好む（Recency bias）・複雑なコードを高評価 | 客観的でない winner 選定 → 次善のコードを採用 | 重み付きスコアリングを厳守 · 定量メトリクスで補完 |
| **MO-08** | **ゾンビブランチ蓄積** | cleanup を忘れて arena/variant-* ブランチが残留 | リポジトリ汚染 · 次セッションでブランチ名衝突 | Cleanup Guarantee Protocol を必ず実行 |
| **MO-09** | **プロンプトコピペ症候群** | 前セッションのプロンプトをそのまま再利用 | 古いファイルパス・陳腐化した仕様 → スコープ違反 | 毎セッションで Scope Lock を再導出 |
| **MO-10** | **統合検証のスキップ** | COLLABORATE で merge 後のビルド・テストを省略 | インターフェース不整合が本番に流出 | VERIFY フェーズ（build + test + codex review + interface check）を必須化 |

---

## 2. 分散システムとしてのマルチエンジン

### エンジンをマイクロサービスとして扱う

```
原則: "Treat agents like code, not chat interfaces."
  — GitHub Blog, Multi-Agent Workflows (2025)

Arena のエンジン呼び出しは分散システムの RPC と同等:
  - 各エンジンは独立したプロセス（codex exec / gemini CLI）
  - 通信はプロンプト（入力）とファイル変更（出力）
  - 障害モード: タイムアウト、スコープ違反、不正出力、API エラー

分散システムの原則を適用:
  1. Design for failure first — 全エンジン呼び出しに失敗ハンドリング
  2. Validate every boundary — Scope Check は契約違反の検出
  3. Expect retries — REFINE は自動リトライ機構
  4. Log intermediate state — variant ごとの review_result 記録
  5. Idempotency — 同じ spec + branch で再実行可能な設計
```

### 契約ベースの通信

```
Anti-pattern: 自然言語のみでエンジン間通信
  → フィールド名のドリフト、型の不整合、暗黙の前提

Best practice: 構造化された契約
  1. Typed Schemas: types.ts を shared_read で共有
  2. Action Constraints: allowed_files / forbidden_files で行動を制限
  3. Acceptance Criteria: 具体的な成功条件で出力を検証
  4. Scope Boundary: COLLABORATE で「自分の担当範囲」を明示
```

---

## 3. 失敗モードと対策マトリクス

| 失敗モード | 検出方法 | 復旧戦略 | 予防策 |
|-----------|---------|---------|--------|
| **エンジンタイムアウト** | CLI 実行時間監視 | 別エンジンでリトライ or abort | プロンプトサイズ制限 · タイムアウト設定 |
| **スコープ違反** | `git diff --name-only` で検出 | `git checkout -- {file}` で revert | forbidden_files リストの徹底 |
| **ビルド失敗** | `npm run build` / 言語別ビルド | DISQUALIFY → 別 variant 採用 | Success Criteria にビルド成功を含める |
| **テスト破壊** | テストスイート実行 | Correctness ペナルティ適用 | テストファイルを allowed_files に含める |
| **依存関係変更** | package.json diff 検出 | 変更を revert | forbidden_files に依存管理ファイルを含める |
| **無出力（no-op）** | `git diff --stat` が空 | プロンプト改善してリトライ | 具体的なファイルパスとアクション指示 |
| **merge コンフリクト** | `git merge` 失敗 | Arena リーダーが手動解決 | COLLABORATE で非重複スコープを徹底 |
| **API エラー（認証/レート制限）** | CLI エラー出力 | 待機後リトライ or 別エンジン | API キー事前検証 · レート制限認識 |

---

## 4. 信頼性パターン

### Circuit Breaker パターン

```
エンジンが連続 N 回失敗 → そのエンジンをセッション内で一時除外

  連続 2 回失敗 → 警告（別アプローチで再試行）
  連続 3 回失敗 → そのエンジンをセッション内で除外
  → Self-Competition に切り替え or 単一エンジン COLLABORATE

Engine Proficiency Matrix の Grade D/F → デフォルト選択から除外
```

### Graceful Degradation

```
全エンジンで Cross-Engine COMPETE 不可 → Self-Competition にフォールバック
Self-Competition も不可 → ABORT + ユーザー通知

COLLABORATE で 1 subtask 失敗:
  → 他の subtask は統合 → PARTIAL 報告 → 失敗 subtask のみ再実行 or 手動対応
```

### Idempotent Execution

```
同じ spec + base_commit でセッションを再実行可能にする:
  1. Branch は常に BASE_COMMIT から作成（dirty state を持ち込まない）
  2. Stash で既存作業を退避
  3. Cleanup で branch/worktree を確実に削除
  4. セッション ID で一意識別
```

---

## 5. Team Mode 固有のリスク

| リスク | 原因 | 対策 |
|-------|------|------|
| **index.lock 競合** | 並列 git 操作 | git worktree で完全分離 |
| **ファイルシステム汚染** | 複数エンジンが同一ディレクトリで動作 | 各 subagent に専用 worktree パス |
| **ブランチ作成競合** | subagent が同時にブランチ作成 | リーダーが事前に全ブランチ・worktree を作成 |
| **Worktree 残留** | cleanup 前に subagent が異常終了 | Cleanup Guarantee Protocol（force remove + prune） |
| **コスト倍増** | 並列実行で全 variant 同時に API コスト発生 | 事前コスト見積もり + 確認ゲート |

---

## 6. Forge との連携

```
Arena での活用:
  1. SPEC フェーズで MO-01〜10 のチェックリストを適用
  2. SCOPE LOCK で契約ベース通信の原則を遵守
  3. REVIEW フェーズで失敗モードマトリクスに基づく検出
  4. CLEANUP で Graceful Degradation とゾンビブランチ防止

品質ゲート:
  - Scope Lock 未設定 → EXECUTE 前にブロック（MO-04 防止）
  - Success Criteria なし → SPEC 段階で要求（MO-03 防止）
  - Cleanup 未実行 → セッション完了前にブロック（MO-08 防止）
  - Cost Estimate 未表示 → 3+ variant 時に警告（MO-06 防止）
```

**Source:** [GitHub Blog: Multi-Agent Workflows](https://github.blog/ai-and-ml/generative-ai/multi-agent-workflows-often-fail-heres-how-to-engineer-ones-that-dont/) · [Google ADK Multi-Agent Patterns](https://developers.googleblog.com/developers-guide-to-multi-agent-patterns-in-adk/) · [NexAI: AI Agent Architecture Patterns 2025](https://nexaitech.com/multi-ai-agent-architecutre-patterns-for-scale/)
