"""
STEP 2: 案件一覧を、criteria.json の判定基準に照らしてClaudeに判定させる。

単語一致ではなく、タイトル・カテゴリー・問合せ先から「意味的に近いか」を
判定させるので、直接その単語が出てこない案件（例：「女性宮家」が
皇室典範の判定基準に引っかかる、など）も拾える設計。

実行には環境変数 ANTHROPIC_API_KEY が必要（GitHub Actionsではsecretsに設定する）。
"""

import json
import os
from anthropic import Anthropic

MODEL = "claude-haiku-4-5-20251001"  # 分類だけなので軽量モデルでコストを抑える


def load_criteria(path: str = "criteria.json") -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_system_prompt(criteria: list[dict]) -> str:
    criteria_text = "\n".join(
        f"{c['id']}. {c['label']}: {c['description']}" for c in criteria
    )
    return f"""あなたは日本の行政パブリックコメント（意見募集案件）を、
以下の11個の判定基準のどれかに構造的に近いかどうかで振り分けるアシスタントです。

# 判定基準
{criteria_text}

# 指示
- タイトル・カテゴリー・問合せ先などの情報から、案件が上記のどれかに
  実質的に関係しそうかを判定してください。
- 単語が完全一致していなくても、内容が構造的に近ければ「該当」としてください
  （例：「女性宮家」は明記されていなくても基準7に該当する、など）。
- 逆に、表面上の単語が似ていても実質的に無関係なら該当としないでください。
- 各案件について、以下のJSON形式で1件ずつ判定結果を返してください。
  他の文章は一切含めないでください。

出力フォーマット（JSON配列）：
[
  {{
    "id": "案件ID",
    "matched": true または false,
    "matched_criteria": [該当する基準のid（複数可、matchedがfalseなら空配列）],
    "reason": "20文字程度の短い判定理由"
  }},
  ...
]
"""


def classify_listings(listings: list[dict], criteria: list[dict]) -> list[dict]:
    client = Anthropic()  # ANTHROPIC_API_KEY を環境変数から自動で読む

    system_prompt = build_system_prompt(criteria)

    # 案件情報をコンパクトにまとめてユーザーメッセージにする
    items_text = "\n".join(
        f"- id: {item['id']} / タイトル: {item['title']} / "
        f"カテゴリー: {item['category']} / 問合せ先: {item['contact']}"
        for item in listings
    )

    response = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        system=system_prompt,
        messages=[{"role": "user", "content": items_text}],
    )

    text = response.content[0].text.strip()
    # コードフェンスが付いてくる場合に備えて除去
    text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(text)


if __name__ == "__main__":
    from fetch_listings import load_listings

    listings = load_listings("sample.xml")
    criteria = load_criteria("criteria.json")

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY が設定されていないため、実際の判定は実行できません。")
        print("GitHub Actionsで動かす際は、リポジトリのsecretsにキーを登録してください。")
    else:
        results = classify_listings(listings, criteria)
        by_id = {r["id"]: r for r in results}

        for item in listings:
            r = by_id.get(item["id"], {})
            mark = "★該当" if r.get("matched") else "　除外"
            print(f"[{mark}] {item['title']}")
            if r.get("matched"):
                print(f"       基準: {r.get('matched_criteria')} / 理由: {r.get('reason')}")
