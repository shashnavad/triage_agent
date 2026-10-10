from dotenv import load_dotenv
load_dotenv()
"""All tunables in one place. Every value can be overridden by an environment variable."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KB_DIR = Path(os.getenv("KB_DIR", ROOT / "kb"))

CLASSIFIER_MODEL = os.getenv("CLASSIFIER_MODEL", "claude-haiku-5-5")
DRAFT_MODEL = os.getenv("DRAFT_MODEL", "claude-sonnet-5-5")
TEMPERATURE = float(os.getenv("TEMPERATURE", "0"))

CONF_THRESHOLD = float(os.getenv("CONF_THRESHOLD", "0.80"))  # below this, a human reviews
RRF_MIN = float(os.getenv("RRF_MIN", "0.015"))               # top KB chunk must score at least this
MAX_CORRECTIONS = int(os.getenv("MAX_CORRECTIONS", "2"))     # redrafts after a failed verification
WORKERS = int(os.getenv("WORKERS", "5"))
DENSE_BACKEND = os.getenv("DENSE_BACKEND", "tfidf")

# USD per million tokens: input, output, cache read, cache write (5 min). Verify at platform.claude.com pricing.
PRICES = {
    "claude-haiku-5-5": (0.10, 0.50, 0.01, 0.125),
    "claude-sonnet-5-5": (2.00, 10.00, 0.10, 2.50),
}
