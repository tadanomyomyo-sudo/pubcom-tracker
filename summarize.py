"""
STEP 3: 判定基準に該当した案件だけ、詳細ページの本文を取ってきて要約する。

前提：e-Govパブコメの詳細ページはサーバーサイドで生成された素のHTML
（classify.pyの判定でJS実行なしに取得できると確認済み）。
もし実際に動かして本文が空だった場合は、requestsをPlaywrightに
差し替える必要がある（そのときはこのファイルのfetch_detail_html()だけ直せばよい）。
"""

import json
import os
import time

import requests
from bs4 import BeautifulSoup
from anthropic import Anthropic

MODEL = "claude-haiku-4-5-20251001"
DETAIL_URL = "https://public-comment.e-gov.go.jp/pcm/detail"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; pubcom-tracker/1.0; personal use)"
}


def fetch_detail_html(item_id: str) -> str:
    """案件詳細ページのHTMLを取得する。"""
    params = {"CLASSNAME": "PCMMSTDETAIL", "id": item_id, "Mode": "0"}
    resp = requests.get(DETAIL_URL, params=params, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return resp.text


def extract_detail_text(html: str) -> str:
    """
    詳細ページのHTMLから、本文らしきテキストだけを抜き出す。
    ページ全体にはヘッダー・フッター・スクリプトも含まれるので、
    見た目上の本文部分のテキストをまとめて取る。
    サイトのマークアップが変わったら、この関数だけ直せばよい。
    """
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "header", "nav", "footer"]):
        tag.decompose()

    text = soup.get_text(separator="\n")
    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines)


def summarize(item: dict, detail_text: str, criteria_labels: list[str]) -> dict:
    client = Anthropic()

    system_prompt = """あなたは日本の行政パブリックコメント（意見募集案件）の内容を、
政治的な関心を持つ一般の読者向けに要約するアシスタントです。

以下のJSON形式で出力してください。他の文章は一切含めないでください。
{
  "summary": "3〜5文程度で、何が変わろうとしているのか、平易な言葉で要約",
  "why_it_matters": "指摘された関心領域（下記）にどう関係するか、1〜2文",
  "deadline": "意見提出の締切（本文中にあれば正確な日時、なければ渡された情報をそのまま）",
  "submission_note": "意見提出先や提出方法についてわかれば一言（なければ空文字）"
}
"""

    user_content = f"""案件タイトル: {item['title']}
関係する関心領域: {', '.join(criteria_labels)}
締切（一覧情報）: {item.get('deadline')}

--- 詳細ページの本文（抜粋） ---
{detail_text[:6000]}
"""

    response = client.messages.create(
        model=MODEL,
        max_tokens=1000,
        system=system_prompt,
        messages=[{"role": "user", "content": user_content}],
    )

    text = response.content[0].text.strip()
    text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(text)


def summarize_matched_items(matched_items: list[dict], criteria_by_id: dict) -> list[dict]:
    """
    matched_items: classify.pyの結果で matched=true だったもの
                   （item本体 + matched_criteria が入っている想定）
    """
    results = []
    for item in matched_items:
        try:
            html = fetch_detail_html(item["id"])
            detail_text = extract_detail_text(html)
            labels = [criteria_by_id[cid]["label"] for cid in item.get("matched_criteria", [])]
            summary = summarize(item, detail_text, labels)
            results.append({**item, **summary})
        except Exception as e:
            # 1件失敗しても全体を止めない。あとで見た目でわかるようにエラーを残す
            results.append({**item, "error": str(e)})
        time.sleep(1)  # サイトへの負荷とAPIレート制限への配慮
    return results


if __name__ == "__main__":
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY が未設定のため、実行できません。")
    else:
        print("このファイルは pipeline.py から呼び出す想定です。単体テストは省略。")
