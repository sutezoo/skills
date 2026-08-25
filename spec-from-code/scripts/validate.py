#!/usr/bin/env python3
"""画面仕様書JSONを検証する（検証三層のうち第一層・第二層の単一ファイル分）。
  第一層: JSON Schema 適合（構造・型・enum・種別ごとの記述義務）
  第二層: lint（スキーマでは書けない相互参照検査。全域性・参照の実在・初期状態・
          親子の表示整合・振る舞いの排他・共通仕様 overrides の実在・実装語の混入）
画面間の到達可能性など全ファイル横断の検査は lint_screens.py が行う。
使い方: python validate.py <spec.json> [--schema <schema.json>] [--common-spec <common-spec.json>]
共通仕様は --common-spec 指定が無ければ、spec の commonSpec フィールド（spec ファイルからの相対パス）を探す。
"""
import sys, json, os, re, argparse

BEHAVIOR_KEYS = ("process", "to", "branches", "undefined", "notApplicable")

def behavior_group(o):
    """振る舞いがどのグループか。defined / branches / undefined / notApplicable / (不明はNone)"""
    present = [k for k in BEHAVIOR_KEYS if k in o]
    has_defined = ("process" in o) or ("to" in o)
    groups = set()
    if has_defined: groups.add("defined")
    if "branches" in o: groups.add("branches")
    if "undefined" in o: groups.add("undefined")
    if "notApplicable" in o: groups.add("notApplicable")
    if len(groups) == 1:
        return groups.pop()
    return None  # 0個（event のみ）または複数（排他違反）

def semantic_errors(d, common_rules=None):
    errs = []
    states = {s["name"] for s in d.get("states", [])}
    events = [e["name"] for e in d.get("events", [])]
    events_set = set(events)
    inits = [s["name"] for s in d.get("states", []) if s.get("initial")]
    if len(inits) != 1:
        errs.append(f"初期状態(initial:true)はちょうど1つであるべき: {inits}")

    nodes = d.get("elements", [])
    # トップレベル名（単独要素・コンテナ）は画面内で一意
    top_names = [n.get("name") for n in nodes]
    for n in set(top_names):
        if top_names.count(n) > 1:
            errs.append(f"トップレベルの要素/コンテナ名「{n}」が重複している")

    # 要素参照の索引: 単独要素は (None, name)、コンテナ内要素は (container, name)
    elem_index = {}
    def check_display(disp, label):
        for st in (disp or {}):
            if st not in states:
                errs.append(f"{label} のdisplayByStateに未定義の状態「{st}」")

    for n in nodes:
        check_display(n.get("displayByState"), f"「{n.get('name')}」")
        if "children" in n:  # コンテナ
            cname = n.get("name")
            child_names = [c.get("name") for c in n["children"]]
            for cn in set(child_names):
                if child_names.count(cn) > 1:
                    errs.append(f"コンテナ「{cname}」内で要素名「{cn}」が重複している")
            for ch in n["children"]:
                elem_index[(cname, ch.get("name"))] = True
                check_display(ch.get("displayByState"), f"要素「{cname}/{ch.get('name')}」")
                # 親子の表示矛盾
                cdisp = n.get("displayByState") or {}
                chdisp = ch.get("displayByState") or {}
                for st in chdisp:
                    cv = cdisp.get(st)
                    if cv and cv.get("visibility") == "hidden" and chdisp[st].get("visibility") != "hidden":
                        errs.append(f"状態「{st}」: コンテナ「{cname}」は非表示だが子「{ch.get('name')}」が{chdisp[st].get('visibility')}")
        else:  # 単独要素
            elem_index[(None, n.get("name"))] = True

    # behaviorMatrix: 参照の実在・排他・全域性
    matrix_states = [b.get("state") for b in d.get("behaviorMatrix", [])]
    for s in set(matrix_states):
        if matrix_states.count(s) > 1:
            errs.append(f"behaviorMatrixに状態「{s}」のエントリが複数ある（状態ごとに1エントリにまとめる）")
    for s in states - set(matrix_states):
        errs.append(f"全域性違反: 状態「{s}」が behaviorMatrix に無い（全状態×全イベントを埋める）")

    for b in d.get("behaviorMatrix", []):
        if b["state"] not in states:
            errs.append(f"behaviorMatrixに未定義の状態「{b['state']}」")
        seen_events = []
        for o in b.get("on", []):
            ev = o.get("event")
            seen_events.append(ev)
            if ev not in events_set:
                errs.append(f"状態「{b['state']}」に未定義のイベント「{ev}」")
            g = behavior_group(o)
            if g is None:
                errs.append(f"「{b['state']}/{ev}」: process/to・branches・undefined・notApplicable のちょうど1つを取るべき（四値の排他）")
            if g == "notApplicable":
                if not (o.get("notApplicable") or {}).get("reason", "").strip():
                    errs.append(f"「{b['state']}/{ev}」: notApplicable の reason が空。発生し得ない根拠を書く")
            tos = ([o["to"]] if o.get("to") else []) + [br.get("to") for br in o.get("branches", [])]
            for t in tos:
                if t and t not in states:
                    errs.append(f"未定義の遷移先「{t}」")
            for br in o.get("branches", []):
                if br.get("undefined") and (("process" in br) or ("to" in br) or ("message" in br)):
                    errs.append(f"「{b['state']}/{ev}」の分岐「{br.get('case')}」: undefined の分岐に process/to/message を書かない")
            src = o.get("source")
            if src:
                key = (src.get("container"), src.get("element"))
                if key not in elem_index:
                    ref = (src.get("container") + "/" if src.get("container") else "") + str(src.get("element"))
                    errs.append(f"イベント「{o.get('event')}」のsourceが指す要素「{ref}」が存在しない")
        # 全域性: この状態の on が events の全件をちょうど1回ずつカバーする
        for ev in seen_events:
            if seen_events.count(ev) > 1:
                errs.append(f"状態「{b['state']}」でイベント「{ev}」のセルが重複している")
        if b["state"] in states:
            for ev in events:
                if ev not in seen_events:
                    errs.append(f"全域性違反: セル「{b['state']}×{ev}」が未記載。process/to・branches・undefined・notApplicable のいずれかを書く")

    # navigation の from/to は自画面を指さない
    nav = d.get("navigation") or {}
    my_id = d.get("id")
    for ep in nav.get("entryPoints", []):
        if ep.get("from") == my_id:
            errs.append("entryPoints の from が自画面を指している")
    for xp in nav.get("exitPoints", []):
        if xp.get("to") == my_id:
            errs.append("exitPoints の to が自画面を指している")

    # overrides と共通仕様の突き合わせ
    overrides = d.get("overrides", [])
    if overrides:
        rules_seen = [ov.get("rule") for ov in overrides]
        for r in set(rules_seen):
            if rules_seen.count(r) > 1:
                errs.append(f"overrides にルール「{r}」の宣言が複数ある")
        if common_rules is None:
            errs.append("overrides があるが共通仕様が見つからない（--common-spec を指定するか、spec の commonSpec にパスを書く）")
        else:
            for r in rules_seen:
                if r not in common_rules:
                    errs.append(f"overrides のルール「{r}」が共通仕様に存在しない")
    return errs

def impl_leak(d):
    # 文字列「値」だけを対象に実装語を探す（キー名は対象外）
    leaks = set()
    # HTTPステータス番号は「ステータス」「HTTP」等の語と共起する場合のみ実装語とみなす
    # （文字数の「500文字」などを誤検出しないため、裸の数値は対象にしない）
    pat = re.compile(r"(useState|setState|serializer|Celery|onClick|onChange|fetch|axios|maxLength|max_length)|window\.\w+|\.delay\(|(?:ステータス|ステータスコード|HTTP)\s*[:：]?\s*\d{3}|\d{3}\s*(?:エラー|レスポンス|ステータス)")
    def scan(v):
        if isinstance(v, str):
            for m in pat.findall(v):
                if m: leaks.add(m)
        elif isinstance(v, dict):
            for val in v.values(): scan(val)
        elif isinstance(v, list):
            for x in v: scan(x)
    scan(d)
    return leaks

def load_common_rules(spec_path, d, common_spec_arg):
    """共通仕様を読み、ルールID集合を返す。見つからなければ None。"""
    path = common_spec_arg
    if not path and d.get("commonSpec"):
        path = os.path.join(os.path.dirname(os.path.abspath(spec_path)), d["commonSpec"])
    if not path or not os.path.exists(path):
        return None, None
    cs = json.load(open(path, encoding="utf-8"))
    return {r["id"] for r in cs.get("rules", [])}, path

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("--schema", default=None)
    ap.add_argument("--common-spec", default=None, dest="common_spec")
    args = ap.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))
    schema_path = args.schema or os.path.join(here, "..", "references", "screen-spec.schema.json")
    d = json.load(open(args.spec, encoding="utf-8"))

    ok = True
    # 第一層: スキーマ適合
    try:
        from jsonschema import Draft202012Validator
        schema = json.load(open(schema_path, encoding="utf-8"))
        serrs = list(Draft202012Validator(schema).iter_errors(d))
        if serrs:
            ok = False
            print("[スキーマ違反]")
            for e in serrs: print("  -", list(e.path), e.message)
        else:
            print("[スキーマ適合] OK")
    except ImportError:
        print("[スキーマ適合] スキップ（jsonschema未インストール）")

    # 第二層: 意味的整合（全域性・参照・排他・overrides）
    common_rules, common_path = load_common_rules(args.spec, d, args.common_spec)
    if common_path:
        print(f"[共通仕様] {common_path} を参照")
    merrs = semantic_errors(d, common_rules)
    if merrs:
        ok = False
        print("[意味的整合違反]")
        for e in merrs: print("  -", e)
    else:
        print("[意味的整合] OK")

    # 実装語の混入
    leaks = impl_leak(d)
    if leaks:
        ok = False
        print("[実装語の混入]", leaks, "→ 画面の振る舞いの言葉に翻訳すること")
    else:
        print("[実装語の混入] なし")

    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
