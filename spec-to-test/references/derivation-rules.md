# 導出規則: screen-spec(JSON) → テスト成果物(JSON)

`spec-from-code` が出力する screen-spec(JSON) の各部位を、テスト技法へ**機械的に**変換する規則。
人の発想に依存せず、同じ spec からは同じテストが出ることを保証する（再現性の核）。
出力の契約は `references/test-spec.schema.json`。

## 入力受け入れ時の検査（最初に必ず行う）

テスト導出の前に、入力 screen-spec の意味的整合を確認する（`spec-from-code/references/screen-spec.schema.md` の整合ルールに準拠）。
スクリプトがあれば `scripts/validate.py <spec.json>` で機械検査する。少なくとも次を確認:

- `states[].initial: true` がちょうど1つ。
- `behaviorMatrix[].state` / `on[].event` が states / events に実在する。
- 遷移先 `to`（branches の to を含む）が states に実在する（null 可）。
- `branches` と `process`/`to` が排他。
- `displayByState` のキーが states に実在する。

不整合があれば、テストを作る前に指摘して止める（壊れた spec から導出しても無駄なケースになる）。

---

## 規則1: constraints + validations → equivalenceClasses（同値分割・境界値）

対象: `elements[]` のうち入力系 kind（テキスト入力・テキストエリア・数値入力・日付入力・選択系）。

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
- 「ある状態で起きないはずのイベント」を確認したい場合は、note に「受け付けない」と明記した遷移を足してよい（状態違反テスト）。

---

## 規則4: elements[].displayByState → displayChecks（状態別の表示・操作）

対象: `displayByState` を持つ全要素（コンテナ・children 含む）。

- 各要素について、`states` 全件 × その要素の `visibility` を `displayChecks[].byState` に展開する。
- `conditional` のときは `condition` も持つ（その条件下でのみ操作可、を確認）。
- 親子整合（コンテナが hidden の状態で子が visible を主張していないか）は入力検査で担保済みとみなす。
- 観点は state×要素のマトリクスで「各状態で各要素が仕様どおり見え/操作できるか」を確認する。

---

## 規則5: elements[].kind → crossCuttingCoverage（横断観点の注入）

`references/heuristics-catalog.md` の §16「kind → 観点マッピング」に従う。これが観点漏れ防止の核。

1. 各 `elements[].kind` を §16 の意味カテゴリに分類し、対応観点を引く。
2. 「画面共通」観点を画面に一度当てる。`states`/`behaviorMatrix` を持つなら H-CONC を当てる。
3. `project-profile.json` の `exclusions[]` に該当する観点を外す。
4. 残った観点を:
   - **入力値系**（H-STR/I18N/NUM/SEC/DATE等）→ その要素の `equivalenceClasses` の無効クラスに吸収（`catalogId` を付ける）。
   - **画面挙動系**（H-NAV/CONC/NET/ENV/DISP等）→ 独立した `viewpoints[]`（`category: "横断観点"`, `technique: "単独確認"` など）に起こす。
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

## 規則7: test-spec → test-items（ケースの機械展開）

test-spec の各導出行を1ケースに変換する。ケースIDは連結で決まる（一意性の核）:

| 導出元 | ケースID | 例 |
| --- | --- | --- |
| equivalenceClasses の class | `<viewpoint>-<classId>` | `T01-EC-I02` |
| equivalenceClasses の boundary | `<viewpoint>-<boundaryId>` | `T01-B03` |
| decisionTables の rule | `<viewpoint>-<ruleId>` | `T03-R2` |
| stateTransitions の transition | `<viewpoint>-<transitionId>` | `T05-TR02` |
| displayChecks の (要素×状態) | `<viewpoint>-<element>-<state>` | `T07-保存ボタン-保存中` |

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
| コンテナ（ダイアログ等）の開閉・閉じ方分岐 | モーダル | デシジョンテーブル |
| kind マッピング由来（画面挙動系） | 横断観点 | 単独確認 |
| 複数画面にまたがる流れ | （scenarios へ） | シナリオ |
