#!/usr/bin/env python3
"""画面仕様書JSONを検証する。スキーマ適合と意味的整合の両方を確認する。
使い方: python validate.py <spec.json> [--schema <schema.json>]
スキーマ未指定時は、このスクリプトと同じ階層構成の references/screen-spec.schema.json を探す。
"""
import sys, json, os, re, argparse

def semantic_errors(d):
    errs = []
    states = {s["name"] for s in d.get("states", [])}
    events = {e["name"] for e in d.get("events", [])}
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

    for b in d.get("behaviorMatrix", []):
        if b["state"] not in states:
            errs.append(f"behaviorMatrixに未定義の状態「{b['state']}」")
        for o in b.get("on", []):
            if o["event"] not in events:
                errs.append(f"状態「{b['state']}」に未定義のイベント「{o['event']}」")
            if "branches" in o and ("process" in o or "to" in o):
                errs.append(f"「{b['state']}/{o['event']}」: branchesとprocess/toは排他")
            tos = ([o["to"]] if o.get("to") else []) + [br.get("to") for br in o.get("branches", [])]
            for t in tos:
                if t and t not in states:
                    errs.append(f"未定義の遷移先「{t}」")
            src = o.get("source")
            if src:
                key = (src.get("container"), src.get("element"))
                if key not in elem_index:
                    ref = (src.get("container") + "/" if src.get("container") else "") + str(src.get("element"))
                    errs.append(f"イベント「{o['event']}」のsourceが指す要素「{ref}」が存在しない")
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

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("--schema", default=None)
    args = ap.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))
    schema_path = args.schema or os.path.join(here, "..", "references", "screen-spec.schema.json")
    d = json.load(open(args.spec, encoding="utf-8"))

    ok = True
    # スキーマ適合
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

    # 意味的整合
    merrs = semantic_errors(d)
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
