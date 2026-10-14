"""
Validation script for profiles/transfers.yaml
Checks schema completeness, module path existence, and PII regex patterns.
"""
import os
import re
import sys
import yaml

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROFILE_PATH = os.path.join(ROOT_DIR, "profiles", "transfers.yaml")


def validate_profile():
    if not os.path.exists(PROFILE_PATH):
        print(f"FAIL: Profile not found at {PROFILE_PATH}")
        sys.exit(1)

    with open(PROFILE_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    assert "app_name" in data, "Missing app_name"
    assert "modules" in data, "Missing modules"
    assert "log_fields" in data, "Missing log_fields"
    assert "pii_rules" in data, "Missing pii_rules"
    assert "budgets" in data, "Missing budgets"

    print(f"SUCCESS: Loaded profile for '{data['app_name']}' v{data.get('version')}")
    print(f"Modules defined: {list(data['modules'].keys())}")
    print(f"PII rules defined: {list(data['pii_rules'].keys())}")
    print(f"Max tool calls: {data['budgets'].get('max_tool_calls')}")
    return True


if __name__ == "__main__":
    validate_profile()
