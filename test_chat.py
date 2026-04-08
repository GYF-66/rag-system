import urllib.request
import json

data = json.dumps({
    "message": "人工智能专业需要学哪些核心课程？",
    "session_id": "test-002"
}).encode("utf-8")

req = urllib.request.Request(
    "http://localhost:8002/api/chat",
    data=data,
    headers={"Content-Type": "application/json"}
)

try:
    r = urllib.request.urlopen(req, timeout=120)
    resp = json.loads(r.read())
    print("=== RESPONSE (前600字) ===")
    print(resp.get("response", "")[:600])
    print("\n=== META ===")
    for k, v in resp.get("metadata", {}).items():
        print(f"  {k}: {v}")
    print(f"  sources_count: {len(resp.get('sources', []))}")
    if resp.get("thinking_process"):
        print("\n=== THINKING (前200字) ===")
        print(resp["thinking_process"][:200])
except urllib.error.HTTPError as e:
    print(f"HTTP Error {e.code}: {e.reason}")
    body = e.read().decode("utf-8", errors="replace")
    print(body[:2000])
