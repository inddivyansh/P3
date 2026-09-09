import json
from src.chat.query_engine import process_query

if __name__ == "__main__":
    queries = [
        "What is the current situation at the India-China border?",
        "Show me articles about Manipur conflict",
        "What defence developments happened recently?",
    ]
    for q in queries:
        print("\n" + "="*70)
        print(f"QUERY: {q}")
        print("="*70)
        res = process_query(q)
        print("TOPIC:", res.get("topic") or res.get("question"))
        print("ASSESSMENT:", str(res.get("current_assessment"))[:150])
        print("SUPPORTING ARTICLES:", len(res.get("supporting_articles") or []))
        if res.get("supporting_articles"):
            for a in res["supporting_articles"][:2]:
                print(f"  - [{a.get('source')}] {a.get('title')}")
