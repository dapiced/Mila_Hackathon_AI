#!/usr/bin/env python3
"""Red-team stress test using the Red Mission dataset (461 prompts).

Sends each prompt from Redmission.xlsx to the KHP chatbot API,
records the response, and saves results to JSON + Excel.

Usage:
    cd ~/team_021/project
    python ../scripts/red_team_redmission.py --username USER --password PASS
    python ../scripts/red_team_redmission.py --username USER --password PASS --start 100 --limit 50
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

BASE_URL = "https://chatbot-app.hackathon.buzzperformancecloud.com"
REQUEST_TIMEOUT = 90
REDMISSION_PATH = Path("/home/dom/Documents/mila/final/Redmission.xlsx")


def login(username: str, password: str) -> str:
    r = requests.post(
        f"{BASE_URL}/auth/login",
        headers={"Content-Type": "application/json"},
        json={"username": username, "password": password},
        timeout=REQUEST_TIMEOUT,
    )
    if r.status_code != 200:
        raise Exception(f"Login failed: {r.status_code} - {r.text}")
    return r.json()["session_token"]


def chat(token: str, message: str, thread_id: str = None) -> tuple:
    r = requests.post(
        f"{BASE_URL}/chat",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={"message": message, "thread_id": thread_id},
        timeout=REQUEST_TIMEOUT,
    )
    if r.status_code != 200:
        raise Exception(f"Chat failed: {r.status_code} - {r.text}")
    data = r.json()
    return data["response"], data["thread_id"]


def logout(token: str):
    try:
        requests.post(
            f"{BASE_URL}/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
            timeout=REQUEST_TIMEOUT,
        )
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Red-team KHP chatbot with Red Mission dataset")
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--input", default=str(REDMISSION_PATH), help="Path to Redmission.xlsx")
    parser.add_argument("--output", default="red_team_v3_results.json")
    parser.add_argument("--start", type=int, default=0, help="Start index (for resuming)")
    parser.add_argument("--limit", type=int, default=0, help="Max prompts to test (0=all)")
    args = parser.parse_args()

    # Load Red Mission data
    print(f"Loading Red Mission data from {args.input}")
    df = pd.read_excel(args.input, sheet_name="QA Test Scenarios")
    print(f"Loaded {len(df)} test scenarios")

    # Resume support: load existing results
    output_path = Path(__file__).resolve().parent.parent / args.output
    existing_results = []
    if output_path.exists() and args.start == 0:
        with open(output_path) as f:
            existing_data = json.load(f)
            existing_results = existing_data.get("results", [])
            if existing_results:
                args.start = len(existing_results)
                print(f"Resuming from index {args.start} ({len(existing_results)} already done)")

    # Slice
    end = args.start + args.limit if args.limit > 0 else len(df)
    subset = df.iloc[args.start:end]
    print(f"Testing prompts {args.start} to {min(end, len(df))-1} ({len(subset)} tests)")

    # Login
    print("Logging in...")
    token = login(args.username, args.password)
    print("Login successful.\n")

    results = existing_results.copy()
    timestamp = datetime.now(timezone.utc).isoformat()

    try:
        for i, (idx, row) in enumerate(subset.iterrows()):
            test_num = row.get("#", idx)
            category = row.get("Category", "")
            severity = row.get("Severity", "")
            title = row.get("Title", "")
            prompt = str(row.get("Test Input (Prompt)", "")).strip()
            expected = str(row.get("Expected Behaviour", "")).strip()

            if not prompt:
                print(f"  [{args.start + i + 1}/{len(df)}] SKIP (empty prompt)")
                continue

            print(f"  [{args.start + i + 1}/{len(df)}] {severity} | {category} | {title[:50]}...", end=" ", flush=True)

            start_time = time.time()
            try:
                response, thread_id = chat(token, prompt)
                latency = round(time.time() - start_time, 2)
                status = "success"
            except Exception as e:
                response = ""
                thread_id = ""
                latency = round(time.time() - start_time, 2)
                status = f"error: {e}"

            results.append({
                "test_num": int(test_num) if pd.notna(test_num) else idx,
                "category": category,
                "severity": severity,
                "title": title,
                "prompt": prompt,
                "expected": expected,
                "response": response,
                "thread_id": thread_id,
                "latency_s": latency,
                "status": status,
            })

            print(f"{status} ({latency}s)")

            # Save progress every 10 tests
            if (i + 1) % 10 == 0:
                _save_results(output_path, results, timestamp)
                print(f"  [Progress saved: {len(results)} results]")

            time.sleep(1)  # Rate limiting

    except KeyboardInterrupt:
        print("\n\nInterrupted! Saving progress...")
    finally:
        logout(token)
        _save_results(output_path, results, timestamp)

    # Summary
    print(f"\nDone! {len(results)} tests completed.")
    print(f"  Successes: {sum(1 for r in results if r['status'] == 'success')}")
    print(f"  Errors: {sum(1 for r in results if r['status'] != 'success')}")
    print(f"  Results saved to: {output_path}")

    # Quick severity breakdown
    for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
        count = sum(1 for r in results if r.get("severity") == sev)
        if count:
            print(f"  {sev}: {count} tested")


def _save_results(output_path, results, timestamp):
    output = {
        "timestamp": timestamp,
        "total_tests": len(results),
        "successes": sum(1 for r in results if r["status"] == "success"),
        "errors": sum(1 for r in results if r["status"] != "success"),
        "results": results,
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
