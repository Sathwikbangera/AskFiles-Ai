"""Simple grounding eval: uploads the sample doc, runs a fixed Q/A set through
the live API, and checks each answer for expected keywords. Requires the
backend to be running (`uvicorn app.main:app`) with real provider credentials.

Usage: python tests/run_eval.py
"""

import json
import os
from pathlib import Path

import requests

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
SAMPLE_DOC = Path(__file__).parent.parent / "data" / "sample_docs" / "sample_policy.txt"
QA_SET = Path(__file__).parent / "qa_eval_set.json"


def main():
    session_id = requests.post(f"{BACKEND_URL}/session").json()["session_id"]

    with open(SAMPLE_DOC, "rb") as f:
        upload = requests.post(
            f"{BACKEND_URL}/upload",
            files={"file": (SAMPLE_DOC.name, f.read())},
            data={"session_id": session_id},
        )
    upload.raise_for_status()
    print(f"Indexed {upload.json()['chunks_indexed']} chunks from {SAMPLE_DOC.name}\n")

    qa_set = json.loads(QA_SET.read_text())
    passed = 0

    for case in qa_set:
        resp = requests.post(
            f"{BACKEND_URL}/chat",
            json={"session_id": session_id, "question": case["question"]},
        )
        resp.raise_for_status()
        answer = resp.json()["answer"].lower()

        hit = any(kw.lower() in answer for kw in case["expected_keywords"])
        passed += hit

        status = "PASS" if hit else "FAIL"
        print(f"[{status}] {case['question']}\n  -> {answer[:200]}\n")

    print(f"Score: {passed}/{len(qa_set)}")


if __name__ == "__main__":
    main()
