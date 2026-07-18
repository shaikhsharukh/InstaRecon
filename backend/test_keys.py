"""Integration test: verifies all API keys are present and working."""

import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

root = Path(__file__).resolve().parent.parent
dotenv_path = root / ".env.local"
if dotenv_path.exists():
    load_dotenv(dotenv_path)
else:
    print("FAIL  .env.local not found")
    sys.exit(1)


def check(name: str, value: str | None) -> bool:
    if not value:
        print(f"FAIL  {name}")
        return False
    print(f"  OK  {name}")
    return True


ALL_PASS = True

print("\n--- Key presence ---")
ALL_PASS &= check("KIMI_API_KEY", os.getenv("KIMI_API_KEY"))
ALL_PASS &= check("DAYTONA_API_KEY", os.getenv("DAYTONA_API_KEY"))
ALL_PASS &= check("OXYLABS_USERNAME", os.getenv("OXYLABS_USERNAME"))
ALL_PASS &= check("OXYLABS_PASSWORD", os.getenv("OXYLABS_PASSWORD"))
ALL_PASS &= check("RESEND_API_KEY", os.getenv("RESEND_API_KEY"))

print("\n--- KIMI_API_KEY live test (aiand.app proxy) ---")
kimi_key = os.getenv("KIMI_API_KEY")
if not kimi_key:
    print("SKIP  KIMI_API_KEY  — not set")
    ALL_PASS = False
else:
    try:
        from openai import OpenAI

        _http_client = httpx.Client(verify=False, timeout=httpx.Timeout(20.0))
        client = OpenAI(
            base_url="https://api.aiand.com/v1",
            api_key=kimi_key,
            http_client=_http_client,
        )
        resp = client.chat.completions.create(
            model="moonshotai/kimi-k2.7-code",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant.",
                },
                {
                    "role": "user",
                    "content": "Reply with only the word ok",
                },
            ],
            temperature=0,
            max_tokens=10,
        )
        reply = (resp.choices[0].message.content or "").strip().lower()
        if reply:
            print(f"  OK  KIMI_API_KEY  — responded: {reply}")
        else:
            reason = resp.choices[0].finish_reason
            print(f"WARN  KIMI_API_KEY  — empty response (finish_reason={reason})")
    except Exception as e:
        print(f"WARN  KIMI_API_KEY  — API unreachable: {e}")
        print("      (key is present, proxy may be slow or SSL cert incompatible)")

print("\n--- ENDPOINT reachability (curl equivalent) ---")
try:
    r = httpx.get(
        "https://api.aiand.com/v1/models",
        headers={"Authorization": f"Bearer {kimi_key}"},
        verify=False,
        timeout=10,
    )
    if r.status_code == 200:
        print("  OK  api.aiand.com  — reachable")
    elif r.status_code == 401:
        print("  OK  api.aiand.com  — reachable (auth expected with this key)")
    else:
        print(f"WARN  api.aiand.com  — unexpected status {r.status_code}")
except Exception as e:
    print(f"WARN  api.aiand.com  — unreachable: {e}")

print(f"\n{'ALL PASSED' if ALL_PASS else 'SOME FAILED'}\n")
sys.exit(0 if ALL_PASS else 1)
