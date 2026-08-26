---
name: spec-to-test
description: screen-spec スキーマのJSON画面仕様書（と共通仕様・プロジェクトプロファイル）を入力に、テスト仕様書(test-spec)・テスト条件表(test-conditions)・テスト実施項目書(test-items)をJSONで導出するスキル。テスト条件表は「何を確かめるか」の全量列挙と「どのレベル（単体/コンポーネント/画面結合/E2E）で確かめるか」の振り分けを分離し、漏れ（未割り当て）と重複（複数レベル割り当て）を機械的に検出できるようにする。テストレベルの振り分け・テストピラミッド・条件の割り出しといった文脈でも使う。テストケースを洗い出す・テスト観点を作る・テスト設計をする・テスト仕様書やテスト項目書を作る、といった依頼で必ず使う。「この画面仕様からテストを作って」「テストケースを起こして」「テスト観点を網羅して」など、明示的に"テスト"の語が無くても、画面仕様(JSON)からテストを設計する文脈なら発火させる。同値分割/境界値分析/デシジョンテーブル/状態遷移といった技法をspecの構造から機械的に導出する。さらに、テスト観点の抜け漏れ・網羅性が心配、絵文字や長文字列の入力・二重送信・ゼロ件表示のような仕様に明記されない汎用観点（横断観点・共通仕様）を押さえたい、という文脈でも必ず使う。入力specが無いときは先に spec-from-code で生成する。
---

# spec-to-test

`spec-from-code` が出力した **screen-spec スキーマのJSON画面仕様書**を入力に、
テスト仕様書とテスト実施項目書を **JSONで** 導出する。
誰が（人間でもAgentでも）同じ spec から作っても、同じテスト集合に着地することが目的（再現性）。

**成果物の役割分担**: 導出されたテストの主な価値は**回帰保護**（今後の変更による挙動の破壊の検出）
にある。いま存在するバグを見つけるのは、実装乖離レポート由来の to-be を期待値とした
ケース（未修正コードで fail する）と、spec 生成段階の全域性検査・乖離検出である。
「テストを回したのに何も出ない」を失敗と誤診しないこと。

## 成果物（すべてJSON）

| 成果物 | 問い | type | 由来 |
| --- | --- | --- | --- |
| テスト仕様書 (test-spec) | 何をテストするか（導出の詳細） | `test-spec` | screen-spec + 共通仕様 から導出 |
| テスト条件表 (test-conditions) | 何を・どのレベルで確かめるか（振り分け） | `test-conditions` | 行は test-spec から機械導出。振り分けは人間が確定 |
| テスト実施項目書 (test-items) | どう実行するか（実行可能ケース） | `test-items` | 手動レベルに割り当てた条件を機械展開 |

**前提**: プロジェクトに1つ `project-profile.json`（横断観点の除外宣言）を用意しておく。
共通仕様（common-spec.json）があれば入力に含める（screen-spec の `commonSpec` が指すファイル。
0件表示・二重送信のような汎用観点の、プロジェクト固有の期待値の導出元になる）。
入力の screen-spec は `spec-from-code` の責務。このスキルは spec を**書かない**。

**鉄則: screen-spec(JSON) → test-spec(JSON) → test-conditions(JSON) → test-items(JSON) の順。下層は上層から機械展開する。逆流させない。** 人間の判断が入るのはテスト条件表の列（振り分け・削減）だけで、行の集合は上層から機械的に決まる。

## 形式の約束

- 入力・出力ともJSON。出力の契約は `references/test-spec.schema.json`（test-spec / test-items を `type` で切替）。
- 用語はすでに screen-spec 側で画面の言葉に翻訳済み。実装語（フレームワーク名・関数名・HTTPステータス番号）を持ち込まない。
- 観点・クラス・境界点・ルール・遷移には必ず一意なIDを振る（これが test-items を一意展開できる核）。

## 参照ファイル

- `references/test-spec.schema.json` — **出力の契約**。作業前に必ず読む。
- `references/derivation-rules.md` — **screen-spec の各部位 → テスト技法への変換規則**。導出の心臓部。必ず読む。
- `references/heuristics-catalog.md` — **横断観点カタログ**（文字種・絵文字・長文字列・二重送信・ゼロ件表示など、specに書かれない汎用観点の網羅リストと §16「kind → 観点マッピング」）。
- `references/wording-rules.md` — **期待値・前提条件の記述品質規則**（観測可能・自己完結）。expected/precondition を書く STEP1・STEP3 で必ず読む。
- `references/examples/example.test-spec.json` / `example.test-conditions.json` / `example.test-items.json` — SCR-030 の完成例（手本）。
- `scripts/check_conditions.py` — テスト条件表の機械検査（割り当ての完全性・トレーサビリティ・停止基準）。
- `references/examples/example.project-profile.json` / `assets/template.project-profile.json` — 横断観点の除外宣言。
- 入力 spec のスキーマ定義は `spec-from-code/references/screen-spec.schema.{json,md}`。
  共通仕様の契約は `spec-from-code/references/common-spec.schema.json`。

---

## STEP 0 — 入力の受け入れ検査

テストを起こす前に、入力 screen-spec(JSON) を機械検査する。

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
- [ ] `undefined: true` の箇所を把握した（STEP1 で openIssues に隔離する）
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
- **expected は観測可能・自己完結な文で起こす**（`wording-rules.md`）。「操作できること」のような痩せた表現にしない。ここで痩せると STEP3 の転記でも痩せたまま降りる。観測できる事実が spec にも共通仕様にも無いものは推測せず openIssues に回す。

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

## STEP 2 — テスト条件表（test-conditions）を作る

`derivation-rules.md` の規則8に従う。**行は機械・列は人間。**

1. **行の導出（機械）**: test-spec の導出行（各 class・各 rule・各 transition・displayChecks の
   各要素・横断/共通仕様の各 viewpoint）を1行1条件で列挙する。`derivedFrom` に行IDを書く。
   boundaries は条件にしない（所属クラス条件のケース展開時の具体値）。条件文は観点のレベルに
   とどめ、具体値・手順を書かない。
2. **重複の統合**: 技法違いで同一の振る舞いを指す行（デシジョンテーブルのルールと同じ遷移を指す
   stateTransition など）は、一方を `removed`（理由: 統合先の条件ID）にする。
3. **振り分けの案（人間が確定）**: 各条件に `levels` を1つ提案する。配置の基準は「その振る舞いを
   観測できる、実行コストが最も低いレベル」。スモークとして意図的に重複させる場合のみ `levels` を複数にし、
   `duplicationReason` を書く。削る条件は `removed.reason` にリスクベースの理由を書く。
4. **停止基準**: 画面結合レベルは、behaviorMatrix の状態を一度ずつ通る状態網羅を上限の目安とする
   （`stopCriterion` に明記）。超える条件は下位レベルへ降ろす。
5. **表の外**: API 契約・DB 制約などの結合部固有の確認、非機能、探索的テストは `outOfScope` に
   列挙し、この表では扱わない。
6. `scripts/check_conditions.py <test-conditions.json> --test-spec <test-spec.json>` で検査する
   （全条件が割り当て済みか理由付き削除済みか、derivedFrom の実在、test-spec 行の取りこぼし、
   重複割り当ての理由、停止基準）。

**振り分けは案として提示し、人間の確定（配置・削減の判断）を経てから STEP 3 に進む。**

### ✅ STEP2 完了条件
- [ ] test-spec の全導出行（boundaries を除く）が条件表の行になっている（check_conditions.py が検査）
- [ ] 全条件が `levels`（割り当て済み）か `removed`（理由付き削除済み）のどちらかである
- [ ] 複数レベルに割り当てた条件すべてに `duplicationReason` がある
- [ ] 削除済みの条件すべてに理由がある（黙って消した行が無い）
- [ ] 画面結合の割り当てが停止基準（状態網羅の目安）に収まっている
- [ ] 振り分けの案を人間がレビュー・確定した

---

## STEP 3 — test-items を展開する

**ほぼ機械作業。** テスト条件表で手動実施のレベル（既定: 画面結合・E2E）に割り当てられた条件だけを、
test-spec の導出行からケースに変換する（規則9）。単体・コンポーネントに割り当てた条件は自動テスト
コードとして実装する（この成果物の外）。ケースIDは連結で決まる:

| 導出元 | ケースID | 例 |
| --- | --- | --- |
| equivalenceClasses の class/boundary | `<viewpoint>-<classId/boundaryId>` | `T01-B03` |
| decisionTables の rule | `<viewpoint>-<ruleId>` | `T04-R3` |
| stateTransitions の transition | `<viewpoint>-<transitionId>` | `T05-TR08` |
| displayChecks の 要素×状態 | `<viewpoint>-<element>-<state>` | `T06-検索ボタン-検索中` |
| 共通仕様ルール由来の観点 | `<viewpoint>-<ruleId>` | `T13-COM-005` |

- 各ケースに precondition / input / operation / expected を埋める。`expected` は test-spec の expected/actions/message を転記。
- **転記は痩せさせない**（`wording-rules.md`）。expected/precondition は観測可能・自己完結な文にする（「操作できること」「表示中状態」で止めない）。ただし整形に使えるのは **spec と共通仕様に実在する事実だけ**（要素名・状態名・メッセージ文言・共通仕様の statement）。観測できる期待値そのものがどちらにも無いものは、ここで埋めず openIssues 由来として扱い、推測で書かない。
- `result` は空（実行時に pass/fail/blocked を記入）。

### ✅ STEP3 完了条件
- [ ] 手動レベルに割り当てた全条件が漏れなくケース化されている（境界値を持つ条件は各境界点に展開）
- [ ] 単体・コンポーネントに割り当てた条件のケースが混ざっていない
- [ ] ケースIDがすべて「viewpoint-導出要素ID」
- [ ] expected が空でない
- [ ] expected / precondition が観測可能・自己完結（`wording-rules.md` のチェックリストを通る）
- [ ] 同じ test-spec と同じ振り分けから作れば誰がやっても同じ cases 集合になる

---

## アンチパターン（避けること）

- **spec を書き直す**: このスキルは spec を入力として受けるだけ。仕様の不足は spec 側（spec-from-code）に戻す。勝手に補完しない。
- **undefined を推測で埋める**: 確定不可は openIssues に隔離。テストケースにしない。
- **notApplicable のセルからテストを作る**: 「発生し得ない」は仕様段階でレビュー済みの宣言。導出対象外（明示的な状態違反テストを足す場合のみ例外。規則3）。
- **branches の取りこぼし**: 全 branch を1ルールずつ展開する。一部だけ作らない。
- **テストレベルごとに独立して設計する**: レベルの境界に落ちる観点が漏れ、重複も見えなくなる。必ず条件表で全量を列挙してから振り分ける。
- **条件を黙って削る・未割り当てのまま残す**: 削減は removed.reason（リスクベース）付きで記録する。「やらないと決めた」と「忘れた」を区別できなくなる。
- **条件表に具体的なテストケースを書く**: 条件は観点のレベルまで。具体値・手順は配置先レベルの実装（test-items または自動テスト）で書く。
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
- **テスト条件 / テスト条件表**: 確かめるべき振る舞いの観点（条件）を全量列挙し、テストレベル（単体・コンポーネント・画面結合・E2E）へ振り分ける表。漏れ=未割り当ての行、重複=複数レベルに割り当てられた行、として機械的に検出できる。
- **テストレベル**: 単体（関数・クラス）、コンポーネント（UI部品をモック応答で）、画面結合（フロント+APIを通した画面）、E2E（実環境の一連の流れ）。条件はその振る舞いを観測できる、実行コストが最も低いレベルに置く。
