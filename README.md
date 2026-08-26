# skills

skills for agents

自分用の Claude Code スキルを置いておくリポジトリ。修正・実験はここで行う。

## 収録スキル

| スキル | 役割 |
| --- | --- |
| [spec-from-code](spec-from-code/) | 実装コード（React + Django 想定）と意図メモ・要件定義書・手書き仕様書を読み合わせ、画面仕様書を screen-spec スキーマの JSON で生成する。コードと意図メモ・仕様書が食い違う場合は意図メモ・仕様書を正とし、差分は実装乖離レポートに残す。共通仕様からの逸脱は overrides で宣言する。 |
| [spec-to-test](spec-to-test/) | screen-spec スキーマの画面仕様書 JSON（と共通仕様）を入力に、テスト仕様書(test-spec)・テスト条件表(test-conditions)・テスト実施項目書(test-items)を JSON で導出する。テスト条件表で条件の全量列挙とテストレベルへの振り分けを分離する。 |

`spec-from-code` → `spec-to-test` の順に繋がる。テストを作りたいが画面仕様書が無い場合は、先に `spec-from-code` で生成する。

## ディレクトリ構成

各スキルは Claude Code のスキル標準構成に従う。

```
<skill-name>/
  SKILL.md      # frontmatter(name, description) + 本文
  references/   # 実行時に必要に応じて読むスキーマ・ルール・例
  assets/       # テンプレート・生成物の例・ビューア
  scripts/      # 補助スクリプト
```

## ローカルで使う

`~/.claude/skills/` 配下に置くか、シンボリックリンクを張る。

```sh
ln -s "$PWD/spec-from-code" ~/.claude/skills/spec-from-code
ln -s "$PWD/spec-to-test"   ~/.claude/skills/spec-to-test
```

## 検証

`spec-from-code` には画面仕様書 JSON のバリデータが付属する。

```sh
python3 spec-from-code/scripts/validate.py <spec.json> [--common-spec <common-spec.json>]
python3 spec-from-code/scripts/lint_screens.py <specディレクトリ> --roots <入口画面ID>
python3 spec-to-test/scripts/check_conditions.py <test-conditions.json> --test-spec <test-spec.json>
# スキーマ適合まで見るなら: pip install jsonschema
```
