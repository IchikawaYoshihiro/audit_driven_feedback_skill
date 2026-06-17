# examples — ADFD の実践サンプル

監査駆動フィードバック開発（ADFD）を具体的な運用に当てはめたサンプルスキル集です。
本体スキル（`../audit-driven-feedback/`）が「方法論と汎用ワークフロー」なのに対し、
ここは「特定領域への適用例」を置きます。

## dependabot-maintenance

Dependabot の「上げられない PR が溜まってメンテ不能になる」問題に ADFD を適用した例。
保留メジャーを **temporary（上流未対応）/ infra（自環境都合）** に分類し、
リポジトリごとの `docs/dependency-debt.md`（負債台帳）と `dependabot.yml` の `ignore` で
**監査可能・再生成抑制**の状態にします。言語非依存・リポジトリ横断で動きます。

背景記事: 「監査駆動フィードバック開発・実践編① Dependabot の上げられない PR を負債台帳で監査可能にする」

> `tools/lint_skill.py` は `SKILL.md` を再帰的に探索するため、本サンプルも CI の lint 対象に含まれます
> （明示指定も可: `python tools/lint_skill.py examples/dependabot-maintenance`）。
>
> **メモ（リリース時）**: 現在の release ワークフローは `audit-driven-feedback/` のみを zip 化します。
> この `examples/` 配下を配布物に含めるか（含めるなら zip 対象の追加、含めないなら README からの導線のみ）を
> リリース時に決めて `.github/workflows/release.yml` を調整してください。
