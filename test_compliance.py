"""
Hackathon Compliance Integration Test
Simulates the exact evaluator flow: POST /api/agent/init -> GET /api/agent/feed

Usage:
    python test_compliance.py
"""
import requests
import json
import time

BASE = "http://127.0.0.1:8000"

def check(condition, label):
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {label}")
    return condition

def main():
    all_pass = True
    print("=" * 60)
    print("STEP 1: POST /api/agent/init")
    print("=" * 60)

    init_payload = {
        "persona": {
            "name": "Ada",
            "domain": "AI Security"
        }
    }
    r = requests.post(f"{BASE}/api/agent/init", json=init_payload)
    print(f"  HTTP Status: {r.status_code}")
    all_pass &= check(r.status_code == 200, "HTTP 200 returned")

    body = r.json()
    print(f"  Response: {json.dumps(body, indent=2)}")
    agent_id = body.get("agentId")
    all_pass &= check(bool(agent_id), "agentId returned in response")
    all_pass &= check(len(agent_id) > 10, "agentId looks like a UUID")

    print("\n" + "=" * 60)
    print("STEP 2: GET /api/agent/feed immediately (expect empty or posts)")
    print("=" * 60)

    r2 = requests.get(f"{BASE}/api/agent/feed", params={"agentId": agent_id})
    print(f"  HTTP Status: {r2.status_code}")
    all_pass &= check(r2.status_code == 200, "HTTP 200 for feed endpoint")
    
    feed_body = r2.json()
    all_pass &= check("posts" in feed_body, '"posts" key exists in response')
    all_pass &= check(isinstance(feed_body.get("posts"), list), '"posts" is a list')
    print(f"  Posts count: {len(feed_body.get('posts', []))}")

    # Validate schema of any existing posts
    posts = feed_body.get("posts", [])
    if posts:
        post = posts[0]
        all_pass &= check("id" in post, "Post has 'id'")
        all_pass &= check("createdAt" in post, "Post has 'createdAt'")
        all_pass &= check("text" in post, "Post has 'text'")
        all_pass &= check("rationale" in post, "Post has 'rationale'")
        all_pass &= check("sources" in post, "Post has 'sources'")
        all_pass &= check(isinstance(post.get("sources"), list), "'sources' is a list")
        all_pass &= check(len(post.get("text", "").split()) <= 100, "Post text <= 100 words")
        # Check createdAt format ends with Z (UTC)
        all_pass &= check(post.get("createdAt", "").endswith("Z"), "createdAt is UTC ISO 8601 (ends with Z)")
    else:
        print("  No posts yet (scheduler has not completed a cycle). Schema check skipped.")

    print("\n" + "=" * 60)
    print("STEP 3: GET /api/agent/feed with unknown agentId (expect 404)")
    print("=" * 60)
    r3 = requests.get(f"{BASE}/api/agent/feed", params={"agentId": "nonexistent-id"})
    all_pass &= check(r3.status_code == 404, "HTTP 404 for unknown agentId")

    print("\n" + "=" * 60)
    print("RESULT")
    print("=" * 60)
    if all_pass:
        print("ALL CHECKS PASSED")
    else:
        print("SOME CHECKS FAILED — review output above")

    print(f"\nAgentId for manual follow-up: {agent_id}")
    print(f"Feed URL: {BASE}/api/agent/feed?agentId={agent_id}")

if __name__ == "__main__":
    main()
