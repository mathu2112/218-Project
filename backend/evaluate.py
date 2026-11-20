"""Run python evaluate.py to compare all policies over the full dataset."""
import json

from simulation import DATES, compare

if __name__ == "__main__":
    print(json.dumps(compare(DATES), indent=2))
