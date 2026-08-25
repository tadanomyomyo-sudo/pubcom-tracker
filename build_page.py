"""
STEP 4: results.json を、GitHub Pagesで見る用のHTML1枚に変換する。

締切が近い順に並べ、締切を過ぎたものは薄く表示する。
"""

import json
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
RESULTS_PATH = DATA_DIR / "results.json"
OUTPUT_DIR = Path(__file__).parent / "docs"
OUTPUT_PATH = OUTPUT_DIR / "index.html"


def parse_deadline(deadline_str: str):
    """
    「2026/09/25 00:00」のような文字列をdatetimeに変換する。
    要約時にAIが自由記述したケースなど、形式が崩れていたらNoneを返す
    （その場合は締切不明として一覧の最後に回す）。
    """
    if not deadline_str:
        return None
    for fmt in ("%Y/%m/%d %H:%M", "%Y/%m/%d"):
        try:
            return datetime.strptime(deadline_str.strip(), fmt)
        except ValueError:
            continue
    return None


def render_item(item: dict, is_expired: bool) -> str:
    css_class = "item expired" if is_expired else "item"
    criteria_labels = item.get("matched_criteria_labels", item.get("matched_criteria", []))
    tags_html = "".join(f'<span class="tag">{label}</span>' for label in criteria_labels)

    return f"""
    <div class="{css_class}">
      <div class="tags">{tags_html}</div>
      <h2><a href="{item.get('link', '#')}" target="_blank" rel="noopener">{item['title']}</a></h2>
      <p class="deadline">締切: {item.get('deadline', '不明')}{' （締切済み）' if is_expired else ''}</p>
      <p class="summary">{item.get('summary', '')}</p>
      <p class="why"><strong>関心領域との関係:</strong> {item.get('why_it_matters', '')}</p>
      {f'<p class="note">{item["submission_note"]}</p>' if item.get('submission_note') else ''}
    </div>
    """


def build():
    if not RESULTS_PATH.exists():
        results = []
    else:
        with open(RESULTS_PATH, encoding="utf-8") as f:
            results = json.load(f)

    now = datetime.now()
    for item in results:
        item["_deadline_dt"] = parse_deadline(item.get("deadline"))

    # 締切が近い順（不明なものは最後）、有効なものを上に
    active = [i for i in results if i["_deadline_dt"] is None or i["_deadline_dt"] >= now]
    expired = [i for i in results if i["_deadline_dt"] is not None and i["_deadline_dt"] < now]
    active.sort(key=lambda i: (i["_deadline_dt"] is None, i["_deadline_dt"] or now))
    expired.sort(key=lambda i: i["_deadline_dt"], reverse=True)

    items_html = "".join(render_item(i, False) for i in active)
    items_html += "".join(render_item(i, True) for i in expired)

    updated_at = now.strftime("%Y年%m月%d日 %H:%M")

    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<title>パブコメトラッカー</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  body {{ font-family: -apple-system, "Hiragino Sans", sans-serif; max-width: 720px;
         margin: 0 auto; padding: 24px 16px; background: #faf9f7; color: #222; }}
  h1 {{ font-size: 1.4rem; }}
  .updated {{ color: #666; font-size: 0.85rem; margin-bottom: 24px; }}
  .item {{ background: white; border-radius: 10px; padding: 16px 20px;
           margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }}
  .item.expired {{ opacity: 0.5; }}
  .item h2 {{ font-size: 1.05rem; margin: 4px 0 8px; }}
  .item h2 a {{ color: #1a1a1a; text-decoration: none; }}
  .item h2 a:hover {{ text-decoration: underline; }}
  .deadline {{ color: #b8460e; font-weight: bold; font-size: 0.9rem; margin: 4px 0; }}
  .expired .deadline {{ color: #888; }}
  .summary {{ font-size: 0.95rem; line-height: 1.6; }}
  .why {{ font-size: 0.88rem; color: #444; background: #f3f0ea; padding: 8px 12px;
          border-radius: 6px; }}
  .note {{ font-size: 0.82rem; color: #666; }}
  .tags {{ margin-bottom: 6px; }}
  .tag {{ display: inline-block; background: #e8e2d8; color: #5c4a2f; font-size: 0.75rem;
          padding: 2px 8px; border-radius: 999px; margin-right: 4px; }}
  .empty {{ color: #666; }}
</style>
</head>
<body>
  <h1>パブコメトラッカー</h1>
  <p class="updated">最終更新: {updated_at}</p>
  {items_html if results else '<p class="empty">該当する案件はまだありません。</p>'}
</body>
</html>
"""

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"{OUTPUT_PATH} を書き出しました（該当{len(results)}件）")


if __name__ == "__main__":
    build()
