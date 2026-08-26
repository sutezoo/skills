"""画面仕様書ファイルの読み込み（generate.py / lint_screens.py 共用）。
JSONとして読めないファイルは黙って読み飛ばさず、呼び出し元に返して報告させる。"""
import glob, json, os

def load_screen_specs(paths):
    """(specs, bad) を返す。
    specs: 読み込めた画面仕様書の (ファイルパス, dict) のリスト（画面ID順）。
           type が "screen" 以外の JSON（共通仕様など）は対象外として除く。
    bad:   JSONとして読めなかったファイルの (パス, エラー概要) のリスト。"""
    files = []
    for p in paths:
        if os.path.isdir(p):
            files += sorted(glob.glob(os.path.join(p, "*.json")))
        else:
            files.append(p)
    specs, bad = [], []
    for f in files:
        try:
            d = json.load(open(f, encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            bad.append((f, str(e)))
            continue
        if isinstance(d, dict) and d.get("type") == "screen" and "id" in d:
            specs.append((f, d))
    specs.sort(key=lambda fd: fd[1]["id"])
    return specs, bad
