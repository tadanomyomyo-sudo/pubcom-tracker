"""
STEP 1: e-GovパブコメのRSSを読んで、案件一覧を取り出すだけのスクリプト。

まだフィルタも要約もしない。「RSSを読むとどんな情報が手に入るか」を
確認するための土台。
"""

import xml.etree.ElementTree as ET

import requests

RSS_URL = "https://public-comment.e-gov.go.jp/rss/pcm_list.xml"

# RSS 1.0 (RDF) の名前空間。e-GovのRSSはこの形式。
NS = {
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "": "http://purl.org/rss/1.0/",
}


def parse_description(desc: str) -> dict:
    """
    <description>の中身は本来こんな文字列で入っている：
      案の公示日：2026/08/25<br/>受付締切日時：2026/09/25 00:00<br/>
      カテゴリー：電気通信<br/>問合せ先（所管省庁・部局名等）：総務省...
    ここから締切・カテゴリー・問合せ先を取り出す。
    """
    fields = {}
    parts = desc.split("<br/>")
    for part in parts:
        if "：" not in part:
            continue
        key, _, value = part.partition("：")
        fields[key.strip()] = value.strip()
    return fields


def _listings_from_root(root) -> list[dict]:
    listings = []
    for item in root.findall("item", NS):
        title = item.find("title", NS).text
        link = item.find("link", NS).text
        desc = item.find("description", NS).text or ""
        fields = parse_description(desc)

        listings.append({
            "id": link.split("id=")[-1].split("&")[0] if "id=" in link else None,
            "title": title,
            "link": link,
            "category": fields.get("カテゴリー"),
            "deadline": fields.get("受付締切日時"),
            "contact": fields.get("問合せ先（所管省庁・部局名等）"),
        })
    return listings


def load_listings(xml_path: str) -> list[dict]:
    """ファイルパスからRSSを読み込む（動作確認・テスト用）"""
    tree = ET.parse(xml_path)
    return _listings_from_root(tree.getroot())


def load_listings_from_string(xml_text: str) -> list[dict]:
    """文字列からRSSを読み込む（fetch_current_listings()から使う）"""
    root = ET.fromstring(xml_text)
    return _listings_from_root(root)


def fetch_current_listings() -> list[dict]:
    """本番用：e-Govから最新のRSSを取得して一覧を返す"""
    resp = requests.get(RSS_URL, timeout=15)
    resp.raise_for_status()
    return load_listings_from_string(resp.text)


if __name__ == "__main__":
    # このサンドボックスは外部ネットワークが制限されているのでサンプルファイルで確認する。
    # 実際の環境（GitHub Actions等）では fetch_current_listings() を使う。
    listings = load_listings("sample.xml")

    print(f"{len(listings)}件の案件を取得しました\n")
    for item in listings:
        print(f"[{item['category']}] {item['title']}")
        print(f"  締切: {item['deadline']}")
        print(f"  ID: {item['id']}")
        print()
