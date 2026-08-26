#!/usr/bin/env python3
"""全画面仕様書を横断する lint（検証三層のうち第二層の横断検査）。
  - 画面IDの一意性（全ファイル）
  - navigation の from/to が実在する画面を指すか（存在しない画面への遷移の検出）
  - 到達可能性: どこからも遷移されない孤立画面の検出（--roots で入口画面を宣言する）
  - entry/exit の相互整合（A→B の出口があるのに B 側に A からの入口が無い、を情報として表示）
各ファイル単体の検証（スキーマ適合・全域性など）は validate.py が行う。CI では両方を回す。
使い方: python lint_screens.py <specディレクトリまたはspec.json...> [--roots SCR-001,SCR-010]
"""
import sys, argparse
from spec_loading import load_screen_specs

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+", help="specディレクトリまたはspecファイル")
    ap.add_argument("--roots", default="", help="入口画面ID（カンマ区切り）。ここに挙げた画面は孤立扱いにしない")
    args = ap.parse_args()

    loaded, bad = load_screen_specs(args.paths)
    specs = {}
    for f, d in loaded:
        specs.setdefault(d["id"], []).append((f, d))
    roots = {r.strip() for r in args.roots.split(",") if r.strip()}
    errs, infos = [], []
    for f, e in bad:
        errs.append(f"JSONとして読めない: {f}（{e}）")

    # IDの一意性
    for sid, entries in specs.items():
        if len(entries) > 1:
            errs.append(f"画面ID「{sid}」が複数ファイルにある: {[f for f, _ in entries]}")
    ids = set(specs.keys())

    # 参照の実在と辺の収集（entryPoints: from→self, exitPoints: self→to）
    edges = set()
    for sid, entries in specs.items():
        _, d = entries[0]
        nav = d.get("navigation") or {}
        for ep in nav.get("entryPoints", []):
            frm = ep.get("from")
            if frm not in ids:
                errs.append(f"{sid}: entryPoints の from「{frm}」に該当する画面仕様書が無い")
            else:
                edges.add((frm, sid))
        for xp in nav.get("exitPoints", []):
            to = xp.get("to")
            if to not in ids:
                errs.append(f"{sid}: exitPoints の to「{to}」に該当する画面仕様書が無い（存在しない画面への遷移）")
            else:
                edges.add((sid, to))

    # 到達可能性: 入って来る辺が無く、roots にも無い画面は孤立
    incoming = {b for (_, b) in edges}
    for sid in sorted(ids):
        if sid not in incoming and sid not in roots:
            errs.append(f"孤立画面: 「{sid}」へはどの画面からも遷移されない（入口画面なら --roots に宣言する）")

    # entry/exit の相互整合（片側だけの宣言を情報として出す。宣言漏れの候補）
    for sid, entries in specs.items():
        _, d = entries[0]
        nav = d.get("navigation") or {}
        declared_out = {xp.get("to") for xp in nav.get("exitPoints", [])}
        declared_in = {ep.get("from") for ep in nav.get("entryPoints", [])}
        for (a, b) in edges:
            if a == sid and b not in declared_out:
                infos.append(f"{sid}: {b} 側の entryPoints にだけ {sid}→{b} の遷移がある（exitPoints への転記漏れの可能性）")
            if b == sid and a not in declared_in:
                infos.append(f"{sid}: {a} 側の exitPoints にだけ {a}→{sid} の遷移がある（entryPoints への転記漏れの可能性）")

    for e in errs: print("[ERROR]", e)
    for i in infos: print("[INFO]", i)
    print(f"画面 {len(ids)} 件 / 遷移 {len(edges)} 件 / エラー {len(errs)} 件")
    sys.exit(1 if errs else 0)

if __name__ == "__main__":
    main()
