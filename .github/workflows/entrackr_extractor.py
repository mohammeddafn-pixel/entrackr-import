import feedparser
import ollama
import json
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

# ================== CONFIG ==================
RSS_URL = "https://news.google.com/rss/search?q=site:entrackr.com+funding&hl=en-IN&gl=IN&ceid=IN:en"
OLLAMA_MODEL = "llama3.1:8b"

SYSTEM_PROMPT = """You are a startup funding data extractor.
Extract funding information ONLY from the headline text provided. Do not guess or use outside knowledge.

Return ONLY a JSON object:
{
  "startup_name": "name of the startup (string or null)",
  "funding_amount": "exact amount as written e.g. '$5 Mn', 'Rs 40 Cr', '$1.5 Mn' (string or null)",
  "funding_round": "round type e.g. 'Seed', 'Pre-Seed', 'Series A', 'Series B' (string or null)",
  "investors": ["investor names mentioned in the headline"],
  "revenue": "revenue figure if mentioned e.g. 'Rs 63 Cr in FY25' (string or null)"
}

Rules:
- Only use what is explicitly in the headline — nothing else.
- If something is not in the headline, set it to null or [].
- Return ONLY valid JSON."""

# ================== FILTER ==================
def is_funding_article(title: str) -> bool:
    title_lower = title.lower()
    keywords = [
        "raises", "raise", "funding", "invest", "series", "seed", "round",
        "crore", "million", "mn", "cr", "pre-seed", "pre series", "pre-series",
        "secures", "bags", "closes", "leads", "backed"
    ]
    return any(k in title_lower for k in keywords)

def is_today(published_str: str) -> bool:
    try:
        pub_date = parsedate_to_datetime(published_str)
        today = datetime.now(timezone.utc).date()
        return pub_date.date() == today
    except Exception:
        return True

# ================== EXTRACT FROM TITLE ==================
def extract_from_title(title: str) -> dict:
    clean_title = title.replace(" - entrackr.com", "").replace(" - Entrackr", "").strip()
    try:
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Headline: {clean_title}"}
            ],
            format="json",
            options={"temperature": 0.0}
        )
        raw = response['message']['content'].strip()
        return json.loads(raw)
    except Exception as e:
        return {"error": str(e)}

# ================== MAIN RUN ==================
def run(limit=10):
    today_str = datetime.now().strftime("%Y-%m-%d")
    print(f"📡 Fetching today's ({today_str}) Entrackr funding headlines...\n")

    feed = feedparser.parse(RSS_URL)

    if not feed or len(feed.entries) == 0:
        print("❌ No articles found in feed.")
        return []

    print(f"Total articles in feed : {len(feed.entries)}")

    todays_entries = [e for e in feed.entries if is_today(e.get("published", ""))]
    print(f"Today's articles       : {len(todays_entries)}\n")

    if not todays_entries:
        print("⚠️  No articles published today yet.")
        return []

    results = []

    for entry in todays_entries[:limit]:
        title = entry.get("title", "")
        published = entry.get("published", "")

        if not is_funding_article(title):
            print(f"⏭️  Skipping : {title[:80]}")
            continue

        clean_title = title.replace(" - entrackr.com", "").strip()
        print(f"🔍 {clean_title}")

        data = extract_from_title(title)

        result = {
            "title": clean_title,
            "published": published,
            **data
        }
        results.append(result)

        print(f"   ✅ Startup   : {data.get('startup_name', 'N/A')}")
        print(f"   💰 Amount    : {data.get('funding_amount', 'N/A')}")
        print(f"   📊 Round     : {data.get('funding_round', 'N/A')}")
        investors = data.get('investors', [])
        print(f"   🏦 Investors : {', '.join(investors) if investors else 'N/A'}")
        print(f"   📈 Revenue   : {data.get('revenue', 'N/A')}")
        print("-" * 80)

    ts = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"entrackr_funding_{ts}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n🎉 Done! Saved {len(results)} deals → {filename}")
    return results

# ================== RUN ==================
if __name__ == "__main__":
    run(limit=10)
