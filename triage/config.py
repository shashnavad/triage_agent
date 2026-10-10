"""All tunables in one place. Every value can be overridden by an environment variable."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KB_DIR = Path(os.getenv("KB_DIR", ROOT / "kb"))

CLASSIFIER_MODEL = os.getenv("CLASSIFIER_MODEL", "claude-3-5-haiku-20241022")
DRAFT_MODEL = os.getenv("DRAFT_MODEL", "claude-3-5-sonnet-20241022")
TEMPERATURE = float(os.getenv("TEMPERATURE", "0"))

CONF_THRESHOLD = float(os.getenv("CONF_THRESHOLD", "0.80"))  # below this, a human reviews
RRF_MIN = float(os.getenv("RRF_MIN", "0.015"))               # top KB chunk must score at least this
MAX_CORRECTIONS = int(os.getenv("MAX_CORRECTIONS", "2"))     # redrafts after a failed verification
WORKERS = int(os.getenv("WORKERS", "5"))
DENSE_BACKEND = os.getenv("DENSE_BACKEND", "tfidf")          # "tfidf" (default) or "minilm"
