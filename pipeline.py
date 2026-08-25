"""
STEP 3.5: fetch_listings / classify / summarize をつなぐパイプライン。

1日1回これを実行する想定（GitHub Actionsから呼ぶ）。

- data/processed_ids.json … これまでに判定した案件IDの記録（再判定を防ぐ）
- data/results.json       … 該当した案件の要約結果の蓄積（GitHub Pagesが読む）
"""

import json
import os
from pathlib import Path

from fetch_listings import fetch_current_listings
from classify import load_criteria, classify_listings
from summarize import summarize_matched_items

DATA_DIR = Path(__file__).parent / "data"
PROCESSED_IDS_PATH = DATA_DIR / "processed_ids.json"
RESULTS_PATH = DATA_DIR / "results.json"


def load_json(path: Path, default):
    if not path.exists():
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def run():
    criteria = load_criteria(Path(__file__).parent / "criteria.json")
    criteria_by_id = {c["id"]: c for c in criteria}

    processed_ids = set(load_json(PROCESSED_IDS_PATH, []))
    results = load_json(RESULTS_PATH, [])

    listings = fetch_current_listings()
    new_listings = [item for item in listings if item["id"] not in processed_ids]

    print(f"取得: {len(listings)}件 / 未処理: {len(new_listings)}件")

    if not new_listings:
        print("新規案件なし。終了します。")
        return

    classifications = classify_listings(new_listings, criteria)
    by_id = {c["id"]: c for c in classifications}

    matched_items = []
    for item in new_listings:
        c = by_id.get(item["id"], {})
        if c.get("matched"):
            matched_items.append({**item, "matched_criteria": c.get("matched_criteria", [])})

    print(f"該当: {len(matched_items)}件")

    if matched_items:
        summarized = summarize_matched_items(matched_items, criteria_by_id)
        results = summarized + results  # 新しいものを先頭に

    # 判定済みIDを記録（該当・除外どちらも記録し、二重処理を防ぐ）
    processed_ids.update(item["id"] for item in new_listings)

    save_json(PROCESSED_IDS_PATH, sorted(processed_ids))
    save_json(RESULTS_PATH, results)

    print(f"results.json を更新しました（累計{len(results)}件）")


if __name__ == "__main__":
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY が未設定です。GitHub Actionsのsecretsに設定してください。")
    else:
        run()
