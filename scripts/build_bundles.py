"""
scripts/build_bundles.py
Validates and manages the 8 Golden Scenario Bundles for TriagePilot.
"""
import os
import json
import yaml

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUNDLES_DIR = os.path.join(ROOT_DIR, "data", "bundles")
SCENARIOS = ["S01", "S02", "S03", "S04", "S06", "S09", "S10", "S11"]


def verify_bundles():
    print(f"Verifying bundles in {BUNDLES_DIR}...")
    all_ok = True
    for sc in SCENARIOS:
        sc_dir = os.path.join(BUNDLES_DIR, sc)
        if not os.path.isdir(sc_dir):
            print(f"[-] Missing bundle directory: {sc}")
            all_ok = False
            continue

        ticket_file = os.path.join(sc_dir, "ticket.json")
        logs_file = os.path.join(sc_dir, "logs.jsonl")
        record_file = os.path.join(sc_dir, "record_snapshot.json")
        gt_file = os.path.join(sc_dir, "ground_truth.yaml")

        for fpath, name in [(ticket_file, "ticket.json"), (logs_file, "logs.jsonl"), (record_file, "record_snapshot.json"), (gt_file, "ground_truth.yaml")]:
            if not os.path.exists(fpath):
                print(f"[-] {sc}: Missing {name}")
                all_ok = False

        if sc == "S06":
            screenshot = os.path.join(sc_dir, "screenshot.png")
            if not os.path.exists(screenshot):
                print(f"[-] S06: Missing screenshot.png")
                all_ok = False

        if sc == "S11":
            followup = os.path.join(sc_dir, "ticket_followup.json")
            if not os.path.exists(followup):
                print(f"[-] S11: Missing ticket_followup.json")
                all_ok = False

        print(f"[+] {sc}: Bundle complete.")

    if all_ok:
        print("\nAll 8 Golden Scenario Bundles verified successfully!")
    return all_ok


if __name__ == "__main__":
    verify_bundles()
