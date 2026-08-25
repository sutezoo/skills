---
name: spec-to-test
description: screen-spec スキーマのJSON画面仕様書（と共通仕様・プロジェクトプロファイル）を入力に、テスト仕様書(test-spec)とテスト実施項目書(test-items)をJSONで導出するスキル。テストケースを洗い出す・テスト観点を作る・テスト設計をする・テスト仕様書やテスト項目書を作る、といった依頼で必ず使う。「この画面仕様からテストを作って」「テストケースを起こして」「テスト観点を網羅して」など、明示的に"テスト"の語が無くても、画面仕様(JSON)からテストを設計する文脈なら発火させる。同値分割/境界値分析/デシジョンテーブル/状態遷移といった技法をspecの構造から機械的に導出する。さらに、テスト観点の抜け漏れ・網羅性が心配、絵文字や長文字列の入力・二重送信・ゼロ件表示のような仕様に明記されない汎用観点（横断観点・共通仕様）を押さえたい、という文脈でも必ず使う。入力specが無いときは先に spec-from-code で生成する。
---

# spec-to-test

`spec-from-code` が出力した **screen-spec スキーマのJSON画面仕様書**を入力に、
テスト仕様書とテスト実施項目書を **JSONで** 導出する。
誰が（人間でもAgentでも）同じ spec から作っても、同じテスト集合に着地することが目的（再現性）。

**成果物の役割分担**: 導出されたテストの主な価値は**回帰保護**（今後の変更で挙動が壊れたときに
教えてくれる）にある。いま存在するバグを見つけるのは、実装乖離レポート由来の to-be を期待値とした
ケース（未修正コードで fail する）と、spec 生成段階の全域性検査・乖離検出である。
「テストを回したのに何も出ない」を失敗と誤診しないこと。

## 成果物（すべてJSON）

| 成果物 | 問い | type | 由来 |
| --- | --- | --- | --- |
| テスト仕様書 (test-spec) | 何をテストするか（導出規則） | `test-spec` | screen-spec + 共通仕様 から導出 |
| テスト実施項目書 (test-items) | どう実行するか（実行可能ケース） | `test-items` | test-spec を機械展開 |

**前提**: プロジェクトに1つ `project-profile.json`（横断観点の除外宣言）を用意しておく。
共通仕様（common-spec.json）があれば入力に含める（screen-spec の `commonSpec` が指すファイル。
0件表示・二重送信のような汎用観点の、プロジェクト固有の期待値の導出元になる）。
入力の screen-spec は `spec-from-code` の責務。このスキルは spec を**書かない**。

**鉄則: screen-spec(JSON) → test-spec(JSON) → test-items(JSON) の順。下層は上層から機械展開する。逆流させない。**

## 形式の約束

- 入力・出力ともJSON。出力の契約は `references/test-spec.schema.json`（test-spec / test-items を `type` で切替）。
- 用語はすでに screen-spec 側で画面の言葉に翻訳済み。実装語（フレームワーク名・関数名・HTTPステータス番号）を持ち込まない。
- 観点・クラス・境界点・ルール・遷移には必ず一意なIDを振る（これが test-items を一意展開できる核）。

## 参照ファイル

- `references/test-spec.schema.json` — **出力の契約**。作業前に必ず読む。
- `references/derivation-rules.md` — **screen-spec の各部位 → テスト技法への変換規則**。導出の心臓部。必ず読む。
- `references/heuristics-catalog.md` — **横断観点カタログ**（文字種・絵文字・長文字列・二重送信・ゼロ件表示など、specに書かれない汎用観点の網羅リストと §16「kind → 観点マッピング」）。
- `references/wording-rules.md` — **期待値・前提条件の記述品質規則**（観測可能・自己完結）。expected/precondition を書く STEP1・STEP2 で必ず読む。
- `references/examples/example.test-spec.json` / `example.test-items.json` — SCR-030 の完成例（手本）。
- `references/examples/example.project-profile.json` / `assets/template.project-profile.json` — 横断観点の除外宣言。
- 入力 spec のスキーマ定義は `spec-from-code/references/screen-spec.schema.{json,md}`。
  共通仕様の契約は `spec-from-code/references/common-spec.schema.json`。

---

## STEP 0 — 入力の受け入れ検査

テストを起こす前に、入力 screen-spec(JSON) を機械検証する。

```
python <spec-from-codeのパス>/scripts/validate.py <spec.json> [--common-spec <common-spec.json>]
```

スキーマ適合（kind の enum・種別ごとの記述義務・振る舞い4値の排他）と lint（全域性・参照の実在・
初期状態がちょうど1つ・overrides の実在など）が通ることを確認する。
**不整合があれば、テストを作らずに指摘して止める**（壊れた spec から導出してもケースが無駄になる）。
スクリプトが実行できない場合のみ `derivation-rules.md` 冒頭の項目を手動で確認する。

### ✅ STEP0 完了条件
- [ ] 入力が screen-spec スキーマ（v2.0）に適合している
- [ ] lint（全域性・参照の実在・排他）に違反がない
- [ ] `undefined: true` の箇所を把握した（STEP2 で openIssues に隔離する）
- [ ] `notApplicable` のセルを把握した（テストを導出しない。規則3）
- [ ] 共通仕様（commonSpec）の有無を確認した（あれば読み込む）

---

## STEP 1 — test-spec を導出する

`references/derivation-rules.md` に従い、screen-spec の各部位を機械的に変換する。**このSTEPは3段**（機能観点→横断観点→共通仕様観点）。

### STEP 1A — 機能観点（spec由来）

| 入力 spec の部位 | 規則 | 出力先 | 技法 |
| --- | --- | --- | --- |
| `elements[].constraints` + `validations` | 規則1 | `equivalenceClasses`（valid/invalid・境界点） | 同値分割+境界値 |
| `behaviorMatrix[].on[].branches` | 規則2 | `decisionTables`（1 branch = 1 rule） | デシジョンテーブル |
| `behaviorMatrix` の state×event×to | 規則3 | `stateTransitions` | 状態遷移 |
| `behaviorMatrix` の `notApplicable` セル | 規則3 | （導出しない。任意で状態違反テスト） | — |
| `elements[].displayByState` | 規則4 | `displayChecks` | 状態別表示 |
| `elements[].emptyBehavior`（一覧の0件） | 規則4b | 独立 viewpoint（expected = emptyBehavior） | 単独確認 |
| `undefined: true` | 規則6 | `openIssues` | （確定不可として隔離） |

- 観点は `viewpoints[]` に起こし、`category` と `technique` を宣言する（対応は derivation-rules の表）。
- **境界値（機械的）**: 範囲が `min〜max` なら min-1 / min / max / max+1 の4点を必ず作る。
- 各 class/boundary/rule/transition に一意なID（EC-/B/R/TR）。
- **expected は観測可能・自己完結な文で起こす**（`wording-rules.md`）。「操作できること」のような痩せた表現にしない。ここで痩せると STEP2 の転記でも痩せたまま降りる。観測できる事実が spec にも共通仕様にも無いものは推測せず openIssues に回す。

### STEP 1B — 横断観点（カタログ由来・観点漏れ防止の核）

`heuristics-catalog.md` の §16「kind → 観点マッピング」に従い、規則5で機械適用する。
kind は enum なので引き当ては表と1対1で決まる。

1. 各 `elements[].kind` を表で引いて観点を得る。画面共通を一度当てる。状態を持つなら H-CONC を当てる。
2. `project-profile.json` の `exclusions[]` に該当する観点を外す。
3. 残りを落とす: **入力値系**はその要素の `equivalenceClasses` の無効クラスに吸収（`catalogId` を付ける）／**画面挙動系**は独立 `viewpoints`（`category: "横断観点"`）にする。
4. **全観点**を `crossCuttingCoverage[]` に `applied`/`excluded`/`n_a` で記録する。**黙って落とさない**（applied は coveredBy、excluded/n_a は reason を必ず書く）。

### STEP 1C — 共通仕様観点（common-spec 由来）

共通仕様がある場合、規則7で全ルールを機械適用する。

1. 共通仕様の `rules[]` を1件ずつ、画面に対象があれば観点（`category: "共通仕様"`、
   `catalogIds: ["COM-xxx"]`）に起こす。無ければ `n_a`（理由付き）で記録する。
2. expected は、画面の `overrides` にそのルールの宣言が**あればその behavior**、無ければ共通仕様の
   `statement` を使う。カタログ観点と重なるルール（二重送信・0件表示など）は観点を統合し、
   期待値は共通仕様側の具体的な文言を使う。
3. 全ルールを `crossCuttingCoverage[]` に記録する（catalogId に COM-xxx）。
4. test-spec の `commonSpecRef` に参照した共通仕様ファイルを書く。

共通仕様が無いプロジェクトではこのSTEPは飛ばし、その旨を報告する（0件表示・二重送信などの
期待値が痩せる。共通仕様の整備を spec 側に促す）。

### ✅ STEP1 完了条件
- [ ] screen-spec の全 branches / 全 state×event（notApplicable・undefined を除く） / 全 displayByState が test-spec に反映されている
- [ ] 一覧要素の emptyBehavior がすべて観点になっている
- [ ] 各 viewpoint に technique が1つ宣言されている
- [ ] 各 class/boundary/rule/transition に一意なID
- [ ] 全 `elements[].kind` が kind マッピングで分類され、`crossCuttingCoverage` に記録されている
- [ ] 横断観点の `excluded` がすべて project-profile の理由に紐づく（黙って省いた観点が無い）
- [ ] 共通仕様がある場合、全ルールが applied / n_a で `crossCuttingCoverage` に記録されている
- [ ] `undefined: true` がすべて openIssues に隔離されている

---

## STEP 2 — test-items を展開する

**ほぼ機械作業。** test-spec の各導出行を1ケースに変換する（規則8）。ケースIDは連結で決まる:

| 導出元 | ケースID | 例 |
| --- | --- | --- |
| equivalenceClasses の class/boundary | `<viewpoint>-<classId/boundaryId>` | `T01-B03` |
| decisionTables の rule | `<viewpoint>-<ruleId>` | `T04-R3` |
| stateTransitions の transition | `<viewpoint>-<transitionId>` | `T05-TR08` |
| displayChecks の 要素×状態 | `<viewpoint>-<element>-<state>` | `T06-検索ボタン-検索中` |
| 共通仕様ルール由来の観点 | `<viewpoint>-<ruleId>` | `T09-COM-003` |

- 各ケースに precondition / input / operation / expected を埋める。`expected` は test-spec の expected/actions/message を転記。
- **転記は痩せさせない**（`wording-rules.md`）。expected/precondition は観測可能・自己完結な文にする（「操作できること」「表示中状態」で止めない）。ただし整形に使えるのは **spec と共通仕様に実在する事実だけ**（要素名・状態名・メッセージ文言・共通仕様の statement）。観測できる期待値そのものがどちらにも無いものは、ここで埋めず openIssues 由来として扱い、推測で書かない。
- `result` は空（実行時に pass/fail/blocked を記入）。

### ✅ STEP2 完了条件
- [ ] test-spec の全導出行が漏れなくケース化されている
- [ ] ケースIDがすべて「viewpoint-導出要素ID」
- [ ] expected が空でない
- [ ] expected / precondition が観測可能・自己完結（`wording-rules.md` のチェックリストを通る）
- [ ] 同じ test-spec から作れば誰がやっても同じ cases 集合になる

---

## アンチパターン（避けること）

- **spec を書き直す**: このスキルは spec を入力として受けるだけ。仕様の不足は spec 側（spec-from-code）に戻す。勝手に補完しない。
- **undefined を推測で埋める**: 確定不可は openIssues に隔離。テストケースにしない。
- **notApplicable のセルからテストを作る**: 「発生し得ない」は仕様段階でレビュー済みの宣言。導出対象外（明示的な状態違反テストを足す場合のみ例外。規則3）。
- **branches の取りこぼし**: 全 branch を1ルールずつ展開する。一部だけ作らない。
- **横断観点・共通仕様ルールを黙って省く**: 当たる観点・ルールは、適用しないなら project-profile で理由付き除外、または crossCuttingCoverage に n_a（理由付き）。黙って消さない。
- **overrides を無視して共通仕様の期待値を使う**: 画面が overrides で逸脱を宣言しているルールは、期待値をその behavior にする。
- **実装語の混入**: screen-spec が翻訳済みの言葉を使う。HTTPステータス番号・関数名を expected に書かない。
- **test-spec に実行手順**: test-spec は導出規則まで。具体操作は test-items。
- **痩せた期待値・前提条件**: 「操作できること」「表示中状態」のような観測不能な表現で止めない（`wording-rules.md`）。ただし観測可能にするための事実が spec にも共通仕様にも無いなら、推測で具体化せず openIssues に回す。上の「spec を書き直す／推測で埋める」と同じ境界線。

## 用語（最小限）

- **同値分割 / 境界値 / デシジョンテーブル / 状態遷移**: それぞれ単一入力の妥当性 / 範囲の境目 / 条件組合せ / 状態×イベントを網羅する技法。
- **横断観点**: spec に明記されないが汎用的に確認すべき観点（文字種・絵文字・レイアウト・操作遷移・並行・通信・環境など）。`heuristics-catalog.md` で網羅的に持ち、kind マッピングで機械適用する。
- **共通仕様**: 日付フォーマット・エラー表示方式・二重送信防止のような画面横断の振る舞いを一箇所に定義したファイル（common-spec.json）。各画面は暗黙に継承し、逸脱は overrides で宣言される。横断観点のうちプロジェクト固有の期待値を持つものの導出元。
- **project-profile**: 横断観点カタログからの除外を、プロジェクト共通で理由付きに宣言するJSON。取捨選択を裁量でなくルール化するためのもの。
