#!/usr/bin/env python3
"""画面仕様書から生成物を作る（検証三層のうち第三層）。手書きの二重管理をやめ、
画面一覧・画面遷移図・入出力一覧はすべて画面仕様書(JSON)からの生成物とする。
  - 画面一覧:   各仕様書の id / title / status から生成
  - 画面遷移図: navigation の参照から Mermaid で生成（個別仕様との乖離が構造的に起きない）
  - 入出力一覧: 要素の dataRef（テーブル・カラム）の集計から生成
使い方: python generate.py <specディレクトリまたはspec.json...> [--out <出力ディレクトリ>]
--out 省略時は標準出力にまとめて出す。
"""
import sys, json, os, glob, argparse

INPUT_KINDS = {"テキスト入力", "テキストエリア", "数値入力", "日付入力", "選択",
               "チェックボックス", "ラジオボタン", "ファイル入力"}

def load_specs(paths):
    files = []
    for p in paths:
        if os.path.isdir(p):
            files += sorted(glob.glob(os.path.join(p, "*.json")))
        else:
            files.append(p)
    specs = []
    for f in files:
        try:
            d = json.load(open(f, encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        if d.get("type") == "screen" and "id" in d:
            specs.append(d)
    return sorted(specs, key=lambda d: d["id"])

def gen_screen_list(specs):
    lines = ["# 画面一覧", "", "| 画面ID | 画面名 | 確定度 |", "| --- | --- | --- |"]
    for d in specs:
        lines.append(f"| {d['id']} | {d.get('title', '')} | {d.get('status', '')} |")
    return "\n".join(lines) + "\n"

def gen_transition_diagram(specs):
    ids = {d["id"] for d in specs}
    titles = {d["id"]: d.get("title", d["id"]) for d in specs}
    edges = {}  # (from, to) -> trigger
    for d in specs:
        nav = d.get("navigation") or {}
        for ep in nav.get("entryPoints", []):
            if ep.get("from") in ids:
                edges.setdefault((ep["from"], d["id"]), ep.get("trigger", ""))
        for xp in nav.get("exitPoints", []):
            if xp.get("to") in ids:
                edges.setdefault((d["id"], xp["to"]), xp.get("trigger", ""))
    lines = ["# 画面遷移図", "", "```mermaid", "flowchart LR"]
    for sid in sorted(ids):
        lines.append(f'  {sid}["{sid} {titles[sid]}"]')
    for (a, b) in sorted(edges):
        trig = edges[(a, b)]
        lines.append(f'  {a} -->|"{trig}"| {b}' if trig else f"  {a} --> {b}")
    lines += ["```", ""]
    return "\n".join(lines)

def gen_io_list(specs):
    lines = ["# 入出力一覧", "",
             "| 画面ID | 要素 | 種別 | 入出力 | テーブル | カラム | 備考 |",
             "| --- | --- | --- | --- | --- | --- | --- |"]
    missing = []
    def walk(d, node, container=None):
        name = (f"{container}/" if container else "") + node.get("name", "")
        ref = node.get("dataRef")
        if ref:
            direction = "入力" if node.get("kind") in INPUT_KINDS else "出力"
            lines.append(f"| {d['id']} | {name} | {node.get('kind','')} | {direction} | "
                         f"{ref.get('table','')} | {ref.get('column','')} | {ref.get('note','')} |")
        for ch in node.get("children", []):
            walk(d, ch, node.get("name"))
    for d in specs:
        for n in d.get("elements", []):
            walk(d, n)
    return "\n".join(lines) + "\n"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    specs = load_specs(args.paths)
    outputs = {
        "screen-list.md": gen_screen_list(specs),
        "transition-diagram.md": gen_transition_diagram(specs),
        "io-list.md": gen_io_list(specs),
    }
    if args.out:
        os.makedirs(args.out, exist_ok=True)
        for name, body in outputs.items():
            with open(os.path.join(args.out, name), "w", encoding="utf-8") as f:
                f.write(body)
            print(f"生成: {os.path.join(args.out, name)}")
    else:
        for name, body in outputs.items():
            print(f"===== {name} =====")
            print(body)

if __name__ == "__main__":
    main()
