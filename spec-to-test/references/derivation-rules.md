# 導出規則: screen-spec(JSON) → テスト成果物(JSON)

`spec-from-code` が出力する screen-spec(JSON) の各部位を、テスト技法へ**機械的に**変換する規則。
人の発想に依存せず、同じ spec からは同じテストが出ることを保証する（再現性の核）。
出力の契約は `references/test-spec.schema.json`。

導出されたテストの主な価値は回帰保護（今後の変更で挙動が壊れたときに教えてくれる）にある。
いま存在するバグを検出するのは、実装乖離レポートの to-be を期待値にしたケース（未修正コードで
fail する）と、spec 生成段階の全域性検査である。「テストを回したのに何も出ない」は、乖離が
無かったという意味であり、導出の失敗ではない。

## 入力受け入れ時の検査（最初に必ず行う）

テスト導出の前に、入力 screen-spec の検証を `spec-from-code/scripts/validate.py` で機械的に行う
（スキーマ適合＋lint。整合ルールの内訳は `spec-from-code/references/screen-spec.schema.md` の
「検証の三層構造」）。共通仕様があれば `--common-spec` で渡す。少なくとも次が保証される:

- スキーマ適合（kind の enum、種別ごとの記述義務、振る舞い4値の排他を含む）。
- `states[].initial: true` がちょうど1つ。
- `behaviorMatrix[].state` / `on[].event` が states / events に実在する。
- 遷移先 `to`（branches の to を含む）が states に実在する（null 可）。
- **全域性**: 全状態×全イベントのセルが process/to・branches・undefined・notApplicable の
  いずれかで埋まっている（未記載セルが無い）。
- `overrides[].rule` が共通仕様に実在する。

不整合があれば、テストを作る前に指摘して spec-from-code 側に差し戻す（壊れた spec から導出しても
無駄なケースになる）。スクリプトが実行できない場合のみ、上記を手動で確認する。

---

## 規則1: constraints + validations → equivalenceClasses（同値分割・境界値）

対象: `elements[]` のうち入力系 kind（テキスト入力・テキストエリア・数値入力・日付入力・選択・
チェックボックス・ラジオボタン・ファイル入力）。

**同値クラス:**
- `required: true` → 無効クラス「未入力/空」を1つ作る。expected は対応する `validations[].message`。
- `validations[]` の各 `condition` → 無効クラス1つ。`id: EC-I0n`、`expected: その message`。
- 上記の補集合として有効クラス「制約をすべて満たす」を1つ作る。`id: EC-V0n`、`kind: valid`。

**境界値（constraints に数値範囲があるときだけ）:**
- `minLength`/`maxLength`（または min/max）があれば **min-1 / min / max / max+1** の4点を作る。
  - 例: `maxLength: 50` かつ `minLength: 1` → `B01:0(下限直前)`, `B02:1(下限境界)`, `B03:50(上限境界)`, `B04:51(上限直後)`。
  - 片側しかなければその側の2点（境界・直後 など）。
- `input` は実値（文字数や数値そのもの）。`expected` は有効/エラーの別。

> `format: email` のような形式制約は境界値を持たず、同値クラス（有効な形式／不正な形式）で扱う。
> kind の enum 化と種別ごとの記述義務により、入力系要素には constraints/validations が必ずあることが
> スキーマで保証されている（「桁数が書かれていないから境界値が作れない」は起きない）。

---

## 規則2: behaviorMatrix[].on[].branches → decisionTables（デシジョンテーブル）

対象: `branches` を持つ振る舞い（結果が複数に枝分かれするもの）。

- 1つの振る舞い（state×event）= 1つのデシジョンテーブル。`viewpoint` に対応観点、`name` に「<state>での<event>」。
- **各 branch = 1ルール**（`rules[]` の1要素、`id: R1, R2...`）。
- `conditions` は branch の `case` を条件文に分解して列挙する。branch が単一の `case` 文字列なら、その case をそのまま1条件として T/F で表してよい（`values: { "<case>": "T" }`、他ルールは "F"）。
- `actions` に branch の `process` を入れる。`message` があれば転記（期待文言）。`to`（遷移先）も action として明記。
- `undefined: true` の branch は decisionTable に入れず、規則6で openIssues に送る。

> branches は「結果による枝分かれ」なので、組合せの網羅は spec 側で既に担保されている。テストはその branch 集合を1ルールずつ展開するだけ。

---

## 規則3: behaviorMatrix の state×event×to → stateTransitions（状態遷移）

対象: `states` が2つ以上あり、遷移を持つ画面。

- `behaviorMatrix[]` を走査し、各 `on[]` を1遷移 `transitions[]`（`id: TR01...`）にする。
  - `branches` がある場合は **branch ごとに1遷移**（case が遷移条件、`to` が遷移先）。
  - `branches` がなければ `process`/`to` で1遷移。
- `from` = その behaviorMatrix の state、`event` = on の event、`to` = 遷移先（null 可＝自己遷移や画面離脱）。
- **`notApplicable` のセルは遷移を導出しない。** 「発生し得ない」は仕様段階でレビュー済みの宣言で
  あり、その担保は displayByState の操作可否検査（規則4）が担う。`undefined` のセルも導出せず、
  規則6で openIssues に送る。
- 「ある状態で起きないはずのイベント」を明示的に確認したい場合は、notApplicable の reason を根拠に、
  note に「受け付けない」と明記した遷移を足してよい（状態違反テスト。任意）。

---

## 規則4: elements[].displayByState → displayChecks（状態別の表示・操作）

対象: `displayByState` を持つ全要素（コンテナ・children 含む）。

- 各要素について、`states` 全件 × その要素の `visibility` を `displayChecks[].byState` に展開する。
- `conditional` のときは `condition` も持つ（その条件下でのみ操作可、を確認）。
- 親子整合（コンテナが hidden の状態で子が visible を主張していないか）は入力検査で担保済みとみなす。
- 観点は state×要素のマトリクスで「各状態で各要素が仕様どおり見え/操作できるか」を確認する。

**規則4b: elements[].emptyBehavior → ゼロ件表示の観点**

- kind が「一覧」の要素は emptyBehavior（0件時の表示・挙動）を必ず持つ（スキーマで保証）。
- 要素ごとに観点1つ（`category: "UI制御"` または独立 viewpoint）を作り、expected は emptyBehavior の
  記述をそのまま使う（観測可能な期待値が spec に在る）。
- `crossCuttingCoverage[]` に H-DISP-01（ゼロ件表示）を `applied`、coveredBy にこの観点IDで記録する。

---

## 規則5: elements[].kind → crossCuttingCoverage（横断観点の注入）

`references/heuristics-catalog.md` の §16「kind → 観点マッピング」に従う。これが観点漏れ防止の核。
kind は screen-spec v2.0 で enum になったため、マッピングの引き当ては表と1対1で決まる。

1. 各 `elements[].kind` を §16 の表で引き、対応観点を得る。
2. 「画面共通」観点を画面に一度当てる。`states`/`behaviorMatrix` を持つなら H-CONC を当てる。
3. `project-profile.json` の `exclusions[]` に該当する観点を外す（記録は残す）。
4. 残った観点を:
   - **入力値系**（H-STR/I18N/NUM/SEC/DATE等）→ その要素の `equivalenceClasses` の無効クラスに吸収（`catalogId` を付ける）。
   - **画面挙動系**（H-NAV/CONC/NET/ENV/DISP等）→ 独立した `viewpoints[]`（`category: "横断観点"`, `technique: "単独確認"` など）に起こす。
   - **共通仕様に対応ルールがあるもの**（0件表示・二重送信など。common-spec の testNote が観点IDを
     指していることが多い）→ 期待値は共通仕様の statement（または画面の overrides）から取る（規則7）。
5. **すべての観点**を `crossCuttingCoverage[]` に記録:
   - `status: "applied"` → `coveredBy` に viewpoint ID または無効クラスID。
   - `status: "excluded"` → `reason` に project-profile の理由。
   - `status: "n_a"` → `reason` に非該当の理由（その kind が画面に無い 等）。

**黙って落とさない。** 除外・非該当も必ず記録する。

---

## 規則6: undefined:true → openIssues（未決事項）

- `behaviorMatrix` の branch や振る舞いに `undefined: true` があれば、`openIssues[]` に `ref`（state/event/element）と `note`（何が不明か）を記録する。
- 未決の箇所はテストケースを確定できないので、decisionTable/stateTransition から除外し、openIssues に隔離する。
- spec 側で確定したら、ここを解消してテストを起こす。

---

## 規則7: 共通仕様 + overrides → 共通仕様の検証観点

対象: screen-spec の `commonSpec` が指す共通仕様（common-spec.json）の全ルール。
共通仕様は「仕様に明記されにくい汎用観点（0件表示・二重送信など）」の期待値の置き場所であり、
横断観点カタログと違ってプロジェクト固有の観測可能な期待値を持つ。

1. 共通仕様の `rules[]` を1件ずつ走査し、画面ごとに次のいずれかに振り分ける:
   - **画面に対象がある** → 観点1つ（`category: "共通仕様"`、`catalogIds: ["COM-xxx"]`）。
     expected は、画面の `overrides` にそのルールの宣言が**あればその behavior**、無ければ共通仕様の
     `statement` をそのまま使う。
   - **画面に対象が無い**（例: 一覧が無い画面の「一覧の0件表示」）→ `crossCuttingCoverage[]` に
     `catalogId: "COM-xxx"`, `status: "n_a"`, reason 付きで記録する。
2. 全ルールを `crossCuttingCoverage[]` に applied / n_a で記録する（catalogId には H- だけでなく
   COM- も入る）。**黙って落とさない。**
3. 横断観点カタログの観点と重なる場合（例: COM-003 二重送信防止 と H-NAV-01）は観点を1つに統合し、
   `catalogIds` に両方のIDを書く。期待値は共通仕様側の具体的な statement を使う（カタログより
   観測可能なため）。
4. overrides に由来する期待値のケースには、判定の根拠が画面固有であることが分かるよう、観点の
   description に「共通仕様 COM-xxx からの逸脱（宣言済み）」と書く。

> 共通仕様が無いプロジェクトではこの規則は空振りする。その場合、0件表示・二重送信などの期待値は
> カタログの「確認内容」止まりになり、観測可能な文言は openIssues に回りやすい。共通仕様の整備を
> spec 側に促すこと。

---

## 規則8: test-spec → test-items（ケースの機械展開）

test-spec の各導出行を1ケースに変換する。ケースIDは連結で決まる（一意性の核）:

| 導出元 | ケースID | 例 |
| --- | --- | --- |
| equivalenceClasses の class | `<viewpoint>-<classId>` | `T01-EC-I02` |
| equivalenceClasses の boundary | `<viewpoint>-<boundaryId>` | `T01-B03` |
| decisionTables の rule | `<viewpoint>-<ruleId>` | `T03-R2` |
| stateTransitions の transition | `<viewpoint>-<transitionId>` | `T05-TR02` |
| displayChecks の (要素×状態) | `<viewpoint>-<element>-<state>` | `T07-保存ボタン-保存中` |
| 共通仕様ルール由来の観点 | `<viewpoint>-<ruleId>` | `T09-COM-003` |

- `expected` は test-spec の `expected`/`actions`/`message` をそのまま転記。
- `result` は空（実行時に pass/fail/blocked を記入）。
- **同じ test-spec から作れば、誰がやっても同じ cases 集合になる**こと。

---

## 観点の起こし方（viewpoints の category と technique）

| 入力 spec の特徴 | category | technique |
| --- | --- | --- |
| 単一要素の constraints/validations（範囲あり） | 入力値 | 同値分割+境界値 |
| 単一要素の validations（形式・選択のみ） | 入力値 | 同値分割 |
| behaviorMatrix の branches（複数結果） | 業務ロジック | デシジョンテーブル |
| 複数 states 間の遷移 | 状態 | 状態遷移 |
| displayByState（状態別の見え方） | UI制御 | 状態別表示 |
| 一覧の emptyBehavior（0件表示） | UI制御 | 単独確認 |
| コンテナ（ダイアログ等）の開閉・閉じ方分岐 | モーダル | デシジョンテーブル |
| kind マッピング由来（画面挙動系） | 横断観点 | 単独確認 |
| 共通仕様のルール（overrides 含む） | 共通仕様 | 単独確認 |
| 複数画面にまたがる流れ | （scenarios へ） | シナリオ |
