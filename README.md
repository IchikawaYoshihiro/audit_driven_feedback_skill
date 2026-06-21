# audit skills

AI エージェント主体の開発で生じる **silent integrity drift（沈黙の整合性ドリフト）** ――
配線漏れ・ドキュメントドリフト・設定ズレ・認可の付け忘れ・データ不変条件の破壊など、
テストもレビューも通るのに本番で静かに壊れる類の欠陥 ―― に対処する、Claude Code / Claude
Agent SDK 向けの汎用監査スキル群です。言語・フレームワーク非依存
（Laravel / Rails / FastAPI / Go / TypeScript いずれにも適用できます）。

姉妹関係にある2つのスキルを収録しています。役割は補完的で重複しません。

| スキル | 問い | 役割 |
| --- | --- | --- |
| **audit-driven-feedback** | **何を**監査し、**どう配線**するか | ドリフトを7分類で診断 → 監査を実装 → CI(予防)+定期(回復)に配線 → 検知→修正→再監査のループを回す |
| **assurance-audit** | その防御は**本当に効いているか** | 各 Protected Behavior を Control(None/Detective/Preventive)→Test→Quality(Strong/Weak)→Status で採点する「採点エンジン」。Coverage Audit ではなく Assurance Audit |

`audit-driven-feedback` が「どの監査を持つべきか」を決め、`assurance-audit` が「ある防御が
本当にテストされ・そのテストが演技でないか」を採点します。以下はまず `audit-driven-feedback`
の説明で、`assurance-audit` は末尾の専用節を参照してください。

---

## audit-driven-feedback

**監査（audit）によるリコンシリエーションループ**で整合性ドリフトを継続的に検知・修正する
方法論です。

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

## assurance-audit

「テストカバレッジ85%・CI 緑」は *どれだけ* テストされたかしか示さず、**守るべき挙動が本当に
ガードされ、それを証明するテストが本物か**は何も語りません。`assurance-audit` は後者を採点します。
**Coverage Audit ではなく Assurance Audit** です。

各 Protected Behavior を次の連鎖で採点します:

```
Inventory → Threat Discovery → Behavior → Control → Test → Quality → Status
 (台帳は    (台帳は十分か?)    (意図)    (None/     (関数   (Strong/  (色)
  あるか?)                              Detective/ 単位)   Weak)
                                       Preventive)
```

- **Step -1 Inventory / -0.5 Threat Discovery**: そもそも「守るべき挙動の台帳」があるか、
  標準タクソノミと差分して十分か。最大の欠陥は弱い Control ではなく *台帳に載っていない挙動*
  であることが多い（例: 認可漏れは思いつくがパスワードリセット悪用は忘れる）。
- **Control 3段階**: None / Detective(事後検知) / Preventive(未然防止)。
- **Quality Strong/Weak**: Expected Outcome を直接 assert していれば Strong、副作用のみ・
  mock で実体隠蔽・間接カバーのみなら Weak。**Weak が Count を上書き**。
- **Status**: 🔴 Missing/Stale Control・Weak Test / 🟡 Structural Weakness・SPOF / 🟢 OK。
  Status(健全性)と Criticality(影響度)は混ぜない。
- **反偽陽性規律**: `grep` 0件 ≠ テスト無し。タグではなく Control 実体名と Expected Outcome
  で再検索する（タグ0件→クラス名で多数発見、が実際に起きる）。

ドメイン固有部分は **ドメインパック**（`references/packs/`）だけ差し替えます。同梱パック:
trading（リファレンス兼ロゼッタストーン・回帰用 golden matrix 付き）/ web-security / saas-billing。

```
assurance-audit/
├── SKILL.md                       # 採点エンジン（4層ワークフロー）
├── references/
│   ├── grading-rubric.md          # Control/Quality/Status の正典（唯一の実体）
│   ├── domain-pack-guide.md       # 自分のドメインパックの書き方
│   └── packs/
│       ├── trading.md             # リファレンスパック + golden matrix
│       ├── web-security.md        # 認可漏れ / 重複登録 / IDOR / レート制限
│       └── saas-billing.md        # 二重課金 / プラン制限回避 / 監査ログ欠落
└── evals/
    └── evals.json                 # 4ケース×軸（framing/反偽陽性/Threat Discovery/Structural Weakness）
```

インストールは `audit-driven-feedback` と同じ要領で、`assurance-audit/` ディレクトリを
`~/.claude/skills/` に置きます。整合性・防御の信頼性・「このガードは本当に効いているか」
といった相談で発火します。

> Release の zip は `audit-driven-feedback-vX.Y.Z.zip` と `assurance-audit-vX.Y.Z.zip` の
> **別ファイル**です（同じ Release に2つ添付されますが、1つのzipに両方入っているわけでは
> ありません）。どちらか一方だけ使いたい場合はそのzipだけ取得して展開すれば足ります。

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
  `audit-driven-feedback-vX.Y.Z.zip` と `assurance-audit-vX.Y.Z.zip` の両方をビルドし、
  GitHub Release に添付します。バージョンはタグで管理します（初回は `v1.0.0`）。

```bash
git tag v1.0.0
git push origin v1.0.0   # → Actions が Release を発行
```

## ライセンス

MIT
