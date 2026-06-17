---
name: dependabot-maintenance
description: |
  Dependabot PRのメンテナンスと依存負債（dependency debt）管理のワークフロー。複数リポジトリのdependabot PRをチェックし、CIが通っているものはマージ、CIが失敗しているものは原因を調査して軽微な修正で対応可能なら修正しマージする。上げられないメジャーバージョンアップは「一時的ブロック（上流未対応→PRは寝かせてrevisitコメント）」と「インフラ依存ブロック（prod環境都合等→PRをClose + dependabot.ymlにignore追加）」に仕分け、いずれもリポジトリ毎の docs/dependency-debt.md に記録して可視化・監査可能にする。マージ後は最新mainをpullしてlint/test/buildのヘルスチェックを行い、最後に構造化レポート（マージ/寝かせ/負債化の件数を含む）を出力する。
  ユーザーが「dependabot」「PR」「マージ」「依存関係」「パッケージ更新」「依存負債」「dependency debt」「上げられないPR」「溜まったPRの整理」「保留PRの棚卸し」などを言及したときや、複数リポジトリのPRメンテ・依存負債の棚卸しを依頼したときに必ず使用すること。
---

# Dependabot PR メンテナンス

## 概要

複数リポジトリのdependabot PRを効率的に処理するワークフロー。安全なマージ・調査・保留の判断を一貫して行い、ヘルスチェックまで完結させる。

## Phase 1: PR 一覧取得（並行実行）

全リポジトリに対して同時にPR情報を取得する。並行実行で時間を節約できる。

```powershell
# 各リポジトリで実行（PowerShellツール使用、Bashツール不可）
Set-Location <repo-path>
gh pr list --author "app/dependabot" --state open --json number,title,mergeable,statusCheckRollup
```

### マージ判断テーブル

| mergeable | CIステータス | 対応 |
|-----------|------------|------|
| MERGEABLE | SUCCESS | マージ ✅ |
| UNKNOWN | SUCCESS | マージ試行（GitHubの計算待ち） |
| MERGEABLE | FAILURE | Phase 2へ（原因調査） |
| MERGEABLE/UNKNOWN | PENDING | 待機または調査 |
| CONFLICTING | - | 保留（手動対応必要） |
| any | - | タイトルにメジャーバージョン変更 → 保留 ⏸️ |

### メジャーバージョン判定

PRタイトルを見て判断する：
- `from 1.x to 2.x` → メジャー（保留）
- `from 9.x to 10.x` → メジャー（保留）
- `from 12.x to 13.x` → メジャー（保留）
- **理由**: メジャーバージョンアップはBreaking Changeを含む可能性が高く、テストが通っても問題が潜む場合がある。必ず保留にして手動確認を求める。
- 保留にしたメジャーは放置せず、**Phase 4 で「出口」を与える**（寝かせ or 負債化）。これをやらないと赤いPRが溜まり、毎週同じPRが再生成され続ける。

## Phase 2: CI失敗の調査

```powershell
# 失敗したrunのIDを取得
gh run list --branch dependabot/<branch>

# ログ確認
gh run view <run-id> --log-failed
```

### よくある失敗パターンと修正

**1. npm peer dependency conflict（eslint バージョン競合）**
- 症状: `npm error ERESOLVE` + `eslint-plugin-react` や他プラグインが `eslint@^9` を要求
- 原因: dependabotがeslint 10に上げたが、プラグインが未対応
- 対応: **保留**（メジャーバージョン変更として扱う）

**2. PHP pint フォーマット違反**
- 症状: `FAIL` + ファイル名一覧
- 修正: `php ./vendor/bin/pint` を実行してコミット
- **注意**: `--test` フラグなしで実行すること（`--test`は確認のみ）

**3. vitest が `.claude/worktrees/` のテストを拾う**
- 症状: 大量の予期しないテスト失敗
- 修正: `vitest.config.ts` の `test` セクションに追加:
  ```ts
  exclude: ['.claude/**', '**/node_modules/**', '**/dist/**'],
  ```

**4. PHP `pdo_sqlite` ドライバ未検出**
- 症状: `could not find driver (Connection: portal, Database: :memory:)`
- 修正: `php.ini` で `extension=pdo_sqlite` と `extension=sqlite3` をアンコメント

**5. インフラCI失敗（`secrets.ACCESS_TOKEN` 未提供）**
- 症状: OpenAPI validation等で `Input required and not supplied: token`
- 原因: Dependabot PRにはsecretsが渡されない仕様
- 対応: 実際のテストが全PASS なら**無視してマージ可**

## Phase 3: マージ実行

```powershell
Set-Location <repo-path>
gh pr merge <number> --merge
```

`--auto` オプションはCIがまだ実行中の場合に便利（CI通過後に自動マージ）。

マージ後、PRが実際にマージされたか確認:
```powershell
gh pr view <number> --json state,mergedAt
```

## Phase 4: 依存負債の管理（保留メジャーの出口）

Phase 1/2 で「保留」と判断したメジャーPRに**出口を与える**フェーズ。放置すると赤いPRが溜まり、毎週同じPRが再生成され、本当に見るべき更新が埋もれる。狙いは「PRを0にする」ことではなく、**上げられない理由を監査可能な形で見える化する**こと。

各保留メジャーを次の2種に仕分ける。判断軸は「**解除条件が上流側か、自分のインフラ側か**」。

### 一時的ブロック（temporary）

上流が追いつけば解消するもの。例: プラグインのエコシステムが新メジャー未対応（eslint-plugin-* が eslint 10 未対応）、依存ライブラリがフレームワーク新メジャー未対応。

- PRは **Close しない**（上流対応後にそのまま上げたい。Closeすると再提案を待つことになる）。
- revisit 条件をPRコメントに残す:
  ```powershell
  Set-Location <repo-path>
  gh pr comment <number> --body "保留(一時的): <理由>。revisit条件: <例: eslint-plugin-vue が eslint 10 をサポートしたら>。docs/dependency-debt.md に記録済み。"
  ```
- `dependabot.yml` の ignore は**使わない**。解消したら通知が欲しいため、PRは開けたままにする。
- **例外（grouped PR の巻き添え）**: dependabot を group 設定（`patterns: ["*"]` 等）で運用していて、ブロック中のメジャーが group に同梱され、**安全な更新（特にセキュリティ修正）まで巻き添えで止めている**場合は、例外的にそのメジャーだけ ignore して group から外す。次回 dependabot が当該メジャーを除いた group を再生成し、安全な更新が流れる。元の grouped PR は Close する（dependabot が自動Closeすることも多い）。この場合は ignore を入れるため**解消通知が来ない** → docs/dependency-debt.md の revisit 条件を具体的に書き、棚卸し時に必ず見直す。単独PR（group化していない）なら巻き添えは起きないので、原則どおり ignore せず開けたまま寝かせる。

### インフラ依存ブロック（infra）

自分たちの環境都合で当面動かせないもの。例: prod の PHP/Node ランタイムが古い、OS制約。解除条件は上流ではなく自分のインフラ更新。

- PRを **Close する**（条件が揃うまで恒久的にムリなので開けておく意味がない）:
  ```powershell
  Set-Location <repo-path>
  gh pr close <number> --comment "保留(インフラ依存): <理由>。解除条件: <例: prod を PHP 8.4 へ>。dependabot.yml に ignore 追加、docs/dependency-debt.md に記録。"
  ```
- `dependabot.yml` の該当エコシステム（composer / npm / github-actions 等）の下に ignore を追加し、**PRの再生成を止める**:
  ```yaml
  ignore:
    - dependency-name: "laravel/framework"
      update-types: ["version-update:semver-major"]
  ```
- ecosystem の取り違えに注意（composer の負債を npm ブロックに書かない）。

### docs/dependency-debt.md への記録（両タイプ共通）

リポジトリの `docs/dependency-debt.md` に1行記録する。無ければ作成、既存行があれば重複させず更新する。これが「監査対象」になる本体。

ファイル新規作成時のテンプレート:
```markdown
# Dependency Debt

上げられないメジャー依存の台帳。dependabot が再提案しても、ここに記録済みのものは「既知の負債」として扱う。
解除条件を満たしたら対応し、この表から削除する。「未マージPR数」ではなくこの表を棚卸し・監査の対象にする。

| Package | Current | Target | Blocker | Type | Revisit condition | Recorded |
|---------|---------|--------|---------|------|-------------------|----------|
| laravel/framework | 12.x | 13.x | prod が PHP 8.3（L13.3+ は Symfony 8 = PHP 8.4 必須） | infra | prod を PHP 8.4+ へ | 2026-06-17 |
```

- **Type**: `temporary` か `infra`。
- **Revisit condition**: 解除条件を具体的に（バージョン・インフラ条件）。「いつか」のような曖昧な記述は禁止 — 監査可能であることが目的。
- **Recorded**: 記録日（今日の日付）。

> 「ブロックされてはいないが工数都合で今回はやらないメジャー」は**負債ではない**。通常のバックログ/タスクとして扱い、この台帳には載せない。debt doc は「今は上げられない*理由がある*」ものだけの台帳。理由がないものを載せると台帳がノイズで埋もれる。

## Phase 5: ヘルスチェック（並行実行）

全リポジトリで最新mainをpullしてから動作確認。並行実行で効率化。

```powershell
# 最新化
Set-Location <repo-path>
git pull
```

### エコシステム別のコマンド

**Node.js (npm)**
```powershell
npm install
npm run lint    # またはリポジトリの設定に応じて
npm run typecheck
npm test
npm run build
```

**Python (uv)**
```powershell
uv sync
uv run poe lint
uv run poe typecheck
uv run pytest
```

**PHP (Composer)**
```powershell
composer install
php ./vendor/bin/pint --test  # フォーマットチェック
php ./vendor/bin/phpstan analyse  # 静的解析
php artisan test  # またはvendor/bin/pest
```

## Phase 6: 構造化レポート

必ず以下のセクション構成でレポートを出力する。セクションが空の場合も見出しを維持する。
冒頭に件数サマリを置く。

```
## サマリ
マージ N 件 / 修正マージ N 件 / 寝かせ（一時的）N 件 / 負債化（インフラ依存）N 件

## マージ済み ✅
| リポジトリ | PR# | 内容 |
|...

## 修正してマージ 🔧
| リポジトリ | PR# | 問題 | 修正内容 |
|...

## 寝かせ: 一時的ブロック 💤
| リポジトリ | PR# | パッケージ | revisit条件 |
|...
※ PRは開いたまま。docs/dependency-debt.md に記録済み（Type: temporary）

## 負債化: インフラ依存ブロック 🧾
| リポジトリ | パッケージ | 解除条件 | ignore追加 | PR |
|...
※ PRはClose。dependabot.yml に ignore 追加 + docs/dependency-debt.md に記録済み（Type: infra）

## ヘルスチェック結果
| リポジトリ | lint | test | build | 備考 |
|...

## 環境問題・注意事項
- 発見した環境固有の問題があれば記載
- なければ「なし」
```

## Windows環境での注意

- **必ずPowerShellツールを使用**（Bashツールが Windows のドライブパス（例: `D:\repos\app`）を扱えない環境の場合）
- heredocは `@'...'@` 形式（bash の `<<'EOF'` は使えない）
- 環境変数は `$env:VAR`
- パス区切りは `\`（バックスラッシュ）

## 作業の優先順位

1. 安全性最優先：メジャーバージョンアップは自動マージしない。テストが通っていても例外なし。
2. 保留を放置しない：保留にしたメジャーは Phase 4 で必ず「寝かせ or 負債化」の出口を与え、debt doc に記録する。これが本スキルの肝。
3. 並行実行で効率化：独立したリポジトリへの操作は同時ターンで実行。
4. スコープ厳守：依頼されていない作業（staleブランチ削除など）は行わない。負債化の ignore 追加・PR Close は「インフラ依存」と確定したものだけ。
5. 最後まで完結：PR処理だけでなく、ヘルスチェックとレポートまで必ず行う。
