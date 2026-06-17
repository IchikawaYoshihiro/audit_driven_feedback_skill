# audit-driven-feedback skill

AI エージェント主体の開発で生じる **silent integrity drift（沈黙の整合性ドリフト）** ――
配線漏れ・ドキュメントドリフト・設定ズレ・認可の付け忘れ・データ不変条件の破壊など、
テストもレビューも通るのに本番で静かに壊れる類の欠陥 ―― を、**監査（audit）による
リコンシリエーションループ**で継続的に検知・修正する方法論を、Claude Code / Claude Agent
SDK の汎用スキルに落とし込んだものです。

言語・フレームワーク非依存。Laravel / Rails / FastAPI / Go / TypeScript いずれにも適用できます。

## これは何をするスキルか

ユーザーが「整合性ガードレールを入れたい」「ポストモーテムを自動チェック化したい」
「AI に実装を任せると配線漏れが怖い」といった相談をしたときに発火し、次の一連を支援します。

1. **Inventory** — 新しい監査を足す前に、既存の監査・テスト・CI ゲートを棚卸し
2. **Diagnose** — 7分類（Parity / Wiring / Data / Docs / Config / Architecture / Process）で何を監査すべきか特定
3. **Prioritize** — 監査を増やしすぎない。実際の事故から1本ずつ育てる
4. **Implement** — 良い監査の5条件（全件列挙・決定的・非ゼロ終了・実行可能メッセージ・例外allowlist）
5. **Wire** — CI（予防）＋ 定期実行（回復）の二段配線
6. **Close the loop** — 検知 → 修正 → 再監査。次の事故はまた監査になって返ってくる

設計思想は GitOps / Kubernetes コントローラの reconciliation（望ましい状態への収束）を、
インフラ運用からアプリ開発工程そのものへ拡張したものです。

## 構成

```
audit-driven-feedback/
├── SKILL.md                      # 方法論 + 6ステップのワークフロー（エントリポイント）
├── references/
│   ├── audit-types.md            # 7分類ごとの検出レシピ（何を全件列挙し、何と比較するか）
│   └── audit-cookbook.md         # 良い監査の作法・CI/定期の配線・運用アンチパターン
└── evals/
    └── evals.json                # 評価セット（4ケース × 4軸：分類精度/過剰監査抑制/ループ閉鎖/二段配線）
```

## インストール（Claude Code）

パーソナルスキルとして使う場合、`audit-driven-feedback/` ディレクトリを
スキル探索パス（`~/.claude/skills/`）に置きます。

### 方法 A: Release の zip を使う（推奨）

[Releases](https://github.com/IchikawaYoshihiro/audit_driven_feedback_skill/releases)
から最新の `audit-driven-feedback-vX.Y.Z.zip` をダウンロードし、展開して中の
`audit-driven-feedback/` ディレクトリを skills フォルダへコピーします。

```bash
# 例: 展開後
# macOS / Linux
cp -r audit-driven-feedback ~/.claude/skills/
# Windows (PowerShell)
Copy-Item -Recurse audit-driven-feedback "$env:USERPROFILE/.claude/skills/"
```

### 方法 B: リポジトリを clone する

```bash
git clone git@github.com:IchikawaYoshihiro/audit_driven_feedback_skill.git
# macOS / Linux
cp -r audit_driven_feedback_skill/audit-driven-feedback ~/.claude/skills/
# Windows (PowerShell)
Copy-Item -Recurse audit_driven_feedback_skill/audit-driven-feedback "$env:USERPROFILE/.claude/skills/"
```

以後、整合性ドリフト・監査・ガードレール関連の相談で自動的に発火します。

## 背景記事

このスキルは Zenn 記事の方法論を実践手順化したものです。記事が思想、スキルが実践手順、
`evals/` が再現性確認、という3点セットで構成されています。

📝 **[AIエージェント時代の品質保証 ― 監査駆動フィードバック開発という考え方](https://zenn.dev/ichikawa_y/articles/audit-driven-feedback-development)**

## 開発 / リリース

- **lint**: `tools/lint_skill.py` がスキルフォーマット（`name` / `description` の制約、
  enum・boolean フィールド、ディレクトリ名一致、本文の相対リンク参照切れ等）を検査します。
  `SKILL.md` を再帰的に探索するので、`examples/` 配下のサンプルも対象です。
  PR / `main` への push で CI が自動実行します。

  手元でも同じ検査を実行できます（PyYAML が無ければ自動で入れて実行します）。

  ```bash
  # macOS / Linux
  bash tools/lint.sh
  # Windows (PowerShell)
  pwsh tools/lint.ps1
  ```

  特定のスキルだけ検査したい場合は引数で指定します（例: `bash tools/lint.sh examples/dependabot-maintenance`）。
  素の Python で直接叩くこともできます（要 `pip install pyyaml`）: `python tools/lint_skill.py`。

- **pre-commit フック（ローカルのガードレール）**: リポジトリに `.githooks/pre-commit` を同梱しています。
  クローンごとに一度だけ有効化すると、コミット前に自動で lint が走り、フォーマット違反を push 前に止められます。

  ```bash
  git config core.hooksPath .githooks
  # macOS / Linux では実行ビットも付けておく（Windows は不要）
  chmod +x .githooks/pre-commit
  ```

  フックは CI と同じ `tools/lint_skill.py` を実行します。どうしても回避したいコミットでは `git commit --no-verify` でバイパスできます。
- **release**: `vX.Y.Z` 形式のタグを push すると、CI が lint を通したうえで
  `audit-driven-feedback-vX.Y.Z.zip` をビルドし、GitHub Release に添付します。
  バージョンはタグで管理します（初回は `v1.0.0`）。

```bash
git tag v1.0.0
git push origin v1.0.0   # → Actions が Release を発行
```

## ライセンス

MIT
