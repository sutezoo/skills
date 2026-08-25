# skills

skills for agents

自分用の Claude Code スキルを置いておくリポジトリ。修正・実験はここで行う。

## 収録スキル

| スキル | 役割 |
| --- | --- |
| [spec-from-code](spec-from-code/) | 実装コード（React + Django 想定）と要件定義書・手書き仕様書を読み合わせ、画面仕様書を screen-spec スキーマの JSON で生成する。コードと仕様書が食い違う場合は仕様書を正とし、差分は実装乖離レポートに残す。 |
| [spec-to-test](spec-to-test/) | screen-spec スキーマの画面仕様書 JSON を入力に、テスト仕様書(test-spec)とテスト実施項目書(test-items)を JSON で導出する。 |

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
python3 spec-from-code/scripts/validate.py <spec.json>
# スキーマ適合まで見るなら: pip install jsonschema
```
