#!/usr/bin/env python3
"""テスト条件表（test-conditions.json）の機械検査。
  - スキーマ適合（jsonschema があれば）
  - closed world: 全条件が levels（割り当て済み）か removed（理由付き削除済み）のどちらか
  - 複数レベル割り当てには duplicationReason が必須
  - derivedFrom が test-spec の導出行に実在する
  - test-spec の導出行（boundaries を除く）に対応する条件行が漏れなくある
  - 停止基準の目安: 画面結合に割り当てた stateTransition 由来の条件数 ≤ 状態数（超えたら警告）
使い方: python check_conditions.py <test-conditions.json> --test-spec <test-spec.json> [--schema <schema.json>]
"""
import sys, json, os, argparse

def testspec_rows(ts):
    """test-spec から条件の導出元となる行IDの集合を返す。boundaries は含めない。"""
    rows = set()
    for ec in ts.get("equivalenceClasses", []):
        for c in ec.get("classes", []):
            rows.add(f'{ec["viewpoint"]}-{c["id"]}')
    for dt in ts.get("decisionTables", []):
        for r in dt.get("rules", []):
            rows.add(f'{dt["viewpoint"]}-{r["id"]}')
    for st in ts.get("stateTransitions", []):
        for tr in st.get("transitions", []):
            rows.add(f'{st["viewpoint"]}-{tr["id"]}')
    for dc in ts.get("displayChecks", []):
        rows.add(f'{dc["viewpoint"]}-{dc["element"]}')
    for v in ts.get("viewpoints", []):
        if v.get("category") in ("横断観点", "共通仕様"):
            rows.add(v["id"])
    return rows

def transition_rows(ts):
    rows = set()
    for st in ts.get("stateTransitions", []):
        for tr in st.get("transitions", []):
            rows.add(f'{st["viewpoint"]}-{tr["id"]}')
    return rows

def state_count(ts):
    states = set()
    for st in ts.get("stateTransitions", []):
        for tr in st.get("transitions", []):
            states.add(tr.get("from"))
            if tr.get("to"):
                states.add(tr["to"])
    return len(states)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("conditions")
    ap.add_argument("--test-spec", dest="test_spec", required=True)
    ap.add_argument("--schema", default=None)
    args = ap.parse_args()

    tc = json.load(open(args.conditions, encoding="utf-8"))
    ts = json.load(open(args.test_spec, encoding="utf-8"))
    errs, warns = [], []

    here = os.path.dirname(os.path.abspath(__file__))
    schema_path = args.schema or os.path.join(here, "..", "references", "test-spec.schema.json")
    try:
        from jsonschema import Draft202012Validator
        schema = json.load(open(schema_path, encoding="utf-8"))
        for e in Draft202012Validator(schema).iter_errors(tc):
            errs.append(f"スキーマ違反 {list(e.path)}: {e.message[:120]}")
    except ImportError:
        print("[スキーマ適合] スキップ（jsonschema未インストール）")

    conds = tc.get("conditions", [])
    ids = [c.get("id") for c in conds]
    for i in set(ids):
        if ids.count(i) > 1:
            errs.append(f"条件ID「{i}」が重複している")

    rows = testspec_rows(ts)
    derived = set()
    for c in conds:
        cid, df = c.get("id"), c.get("derivedFrom")
        has_levels, has_removed = "levels" in c, "removed" in c
        if has_levels == has_removed:
            errs.append(f"{cid}: levels（割り当て）か removed（理由付き削除）のちょうど一方を持つべき")
        if has_levels and len(c["levels"]) >= 2 and not c.get("duplicationReason"):
            errs.append(f"{cid}: 複数レベルに割り当てるなら duplicationReason が必須")
        if has_removed and not (c["removed"].get("reason") or "").strip():
            errs.append(f"{cid}: removed の reason が空。リスクベースの理由か統合先を書く")
        if df not in rows:
            errs.append(f"{cid}: derivedFrom「{df}」が test-spec の導出行に存在しない")
        derived.add(df)

    for r in sorted(rows - derived):
        errs.append(f"取りこぼし: test-spec の導出行「{r}」に対応する条件が無い")

    # 停止基準（目安なので警告）
    tr_rows = transition_rows(ts)
    integ = [c for c in conds
             if "levels" in c and "画面結合" in c["levels"] and c.get("derivedFrom") in tr_rows]
    n_states = state_count(ts)
    if n_states and len(integ) > n_states:
        warns.append(f"画面結合に割り当てた遷移条件が {len(integ)} 件あり、状態数 {n_states}（状態網羅の目安）を超えている。下位レベルへ降ろせないか検討する")

    assigned = sum(1 for c in conds if "levels" in c)
    removed = sum(1 for c in conds if "removed" in c)
    for e in errs: print("[ERROR]", e)
    for w in warns: print("[WARN]", w)
    print(f"条件 {len(conds)} 件（割り当て済み {assigned} / 削除済み {removed}）/ エラー {len(errs)} 件")
    sys.exit(1 if errs else 0)

if __name__ == "__main__":
    main()
