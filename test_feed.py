"""
Feed Response Checker
Checks the current state of a NEXUS agent feed and validates every post against the evaluator schema.

Usage:
    python3 test_feed.py <agentId>
    python3 test_feed.py   (auto-discovers the latest agentId from /api/agent/init)
"""
import sys
import requests
import json
from datetime import datetime, timezone

BASE = "http://127.0.0.1:8000"

def check(condition, label, detail=""):
    status = "PASS" if condition else "FAIL"
    line = f"  [{status}] {label}"
    if detail:
        line += f"  →  {detail}"
    print(line)
    return condition

def validate_post(post, index):
    ok = True
    print(f"\n  --- Post #{index + 1} ---")

    # ID
    ok &= check(bool(post.get("id")), "Has 'id'", post.get("id", "(missing)"))

    # createdAt — must be ISO 8601 UTC ending in Z
    created_at = post.get("createdAt", "")
    ok &= check(bool(created_at), "Has 'createdAt'", created_at)
    ok &= check(created_at.endswith("Z"), "createdAt ends with Z (UTC)", created_at)
    try:
        datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%SZ")
        ok &= check(True, "createdAt is valid ISO 8601")
    except Exception:
        ok &= check(False, "createdAt is valid ISO 8601", f"parse failed: {created_at}")

    # text
    text = post.get("text", "")
    ok &= check(bool(text), "Has 'text'")
    word_count = len(text.split())
    ok &= check(word_count <= 100, f"text <= 100 words", f"{word_count} words")
    ok &= check(word_count > 5, f"text is not empty/trivial", f"{word_count} words")

    # rationale
    rationale = post.get("rationale", "")
    ok &= check(bool(rationale), "Has 'rationale'", rationale[:80] + "..." if len(rationale) > 80 else rationale)
    ok &= check(rationale != "Error.", "rationale is not error placeholder")

    # sources
    sources = post.get("sources", [])
    ok &= check(isinstance(sources, list), "sources is a list")
    ok &= check(len(sources) > 0, "At least one source URL", str(sources))
    for url in sources:
        ok &= check(url.startswith("http"), f"Source is a valid URL", url)

    print(f"  Text preview: \"{text[:120]}{'...' if len(text) > 120 else ''}\"")
    return ok

def main():
    # Resolve agentId
    agent_id = sys.argv[1] if len(sys.argv) > 1 else None

    if not agent_id:
        print("No agentId provided. Initializing a new agent to test with...")
        r = requests.post(f"{BASE}/api/agent/init", json={"persona": {"name": "Ada", "domain": "AI Security"}})
        if r.status_code != 200:
            print(f"  FAIL: Could not init agent. Status: {r.status_code}")
            sys.exit(1)
        agent_id = r.json().get("agentId")
        print(f"  Created agentId: {agent_id}")

    print(f"\n{'=' * 60}")
    print(f"FEED RESPONSE CHECK")
    print(f"AgentId: {agent_id}")
    print(f"{'=' * 60}")

    r = requests.get(f"{BASE}/api/agent/feed", params={"agentId": agent_id})
    all_pass = True

    all_pass &= check(r.status_code == 200, f"HTTP 200 from feed endpoint", f"got {r.status_code}")

    if r.status_code != 200:
        print(f"\n  Response body: {r.text}")
        sys.exit(1)

    body = r.json()
    all_pass &= check("posts" in body, '"posts" key exists in response')
    all_pass &= check(isinstance(body.get("posts"), list), '"posts" is a list')

    posts = body.get("posts", [])
    print(f"\n  Total posts in feed: {len(posts)}")

    if not posts:
        print("\n  No posts yet. The scheduler has not completed a cycle.")
        print(f"  Check again in a few minutes:\n  python3 test_feed.py {agent_id}")
        print(f"\n  Feed URL: {BASE}/api/agent/feed?agentId={agent_id}")
        return

    # Check posts are newest-first (reverse chronological)
    if len(posts) > 1:
        try:
            t1 = datetime.strptime(posts[0]["createdAt"], "%Y-%m-%dT%H:%M:%SZ")
            t2 = datetime.strptime(posts[1]["createdAt"], "%Y-%m-%dT%H:%M:%SZ")
            all_pass &= check(t1 >= t2, "Posts are in reverse chronological order (newest first)")
        except Exception:
            pass

    # Check all IDs are unique
    ids = [p.get("id") for p in posts]
    all_pass &= check(len(ids) == len(set(ids)), f"All post IDs are unique", f"{len(ids)} posts")

    # Validate each post
    for i, post in enumerate(posts):
        all_pass &= validate_post(post, i)

    print(f"\n{'=' * 60}")
    print("RESULT")
    print(f"{'=' * 60}")
    if all_pass:
        print("ALL CHECKS PASSED")
    else:
        print("SOME CHECKS FAILED — review output above")

    print(f"\nFeed URL: {BASE}/api/agent/feed?agentId={agent_id}")
    print(f"Raw feed JSON:\n{json.dumps(body, indent=2)[:2000]}")

if __name__ == "__main__":
    main()
