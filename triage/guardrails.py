"""Input sanitising (PII masking, injection stripping) and output safety checks. No LLM calls here."""
import re

CARD = re.compile(r"\b(?:\d[ -]?){13,19}\b")
CVV = re.compile(r"(?i)\b(?:cvv|cvc|cid)\b\W{0,3}\d{3,4}")
EXPIRY = re.compile(r"(?i)\bexp(?:iry|iration)?(?:\s*date)?\W{0,3}\d{1,2}\s*/\s*\d{2,4}")
SECRET = re.compile(r"(?i)\b(?:(?:sk|pk|key|api)[-_][A-Za-z0-9_\-]{16,}|bearer\s+[A-Za-z0-9._\-]{20,})")

INJECTION = [re.compile(p, re.I) for p in (
    r"\bsystem note\b",
    r"\b(?:ignore|disregard|forget)\b.{0,30}\b(?:instructions|rules|prompt)\b",
    r"\badmin override\b",
    r"\byou are now\b",
    r"\bclassify (?:this )?(?:ticket )?as\b",
    r"\binclude\b.{0,40}\bapi key\b",
    r"\b(?:reveal|print|dump|show)\b.{0,30}\b(?:system prompt|api key)\b",
)]

UNSAFE_OUTPUT = [re.compile(p, re.I) for p in (
    r"\b(?:send|email|share|provide|reply with)\b.{0,40}\b(?:password|api key|card number|cvv)\b",
    r"\bwe (?:will|can|'ll) (?:charge|release|delete|refund|reset)\b",
    r"\bi(?:'ve| have) (?:charged|released|deleted|refunded|reset)\b",
)]
NEGATION = re.compile(r"(?i)\b(?:never|do not|don't|cannot|can't|won't|will not|not)\b")


def _luhn(digits: str) -> bool:
    total = 0
    for i, ch in enumerate(reversed(digits)):
        n = int(ch)
        if i % 2:
            n = n * 2 - 9 if n * 2 > 9 else n * 2
        total += n
    return total % 10 == 0


def _mask_cards(text: str) -> tuple[str, bool]:
    hit = False

    def sub(m):
        nonlocal hit
        digits = re.sub(r"\D", "", m.group())
        if 13 <= len(digits) <= 19 and _luhn(digits):
            hit = True
            return "[REDACTED_PAYMENT_DATA]"
        return m.group()

    return CARD.sub(sub, text), hit


def sanitize(text: str) -> dict:
    """Mask payment data and secrets, drop lines that look like instructions aimed at the AI."""
    text, card = _mask_cards(text)
    text, n_cvv = CVV.subn("[REDACTED_PAYMENT_DATA]", text)
    text, n_exp = EXPIRY.subn("[REDACTED_PAYMENT_DATA]", text)
    text, n_secret = SECRET.subn("[REDACTED_SECRET]", text)

    kept, injected = [], False
    for line in text.splitlines():
        if any(p.search(line) for p in INJECTION):
            injected = True
            kept.append("[REMOVED: suspected prompt injection]")
        else:
            kept.append(line)
    return {
        "text": "\n".join(kept).strip(),
        "injection_flagged": injected,
        "sensitive_flagged": bool(card or n_cvv or n_exp or n_secret),
    }


def check_output(draft: str) -> list[str]:
    """Deterministic checks on a draft reply. Returns a list of problems, empty if clean."""
    issues = []
    if _mask_cards(draft)[1] or "[REDACTED" in draft:
        issues.append("draft contains card data or a redaction marker")
    for sentence in re.split(r"(?<=[.!?\n])\s+", draft):
        if NEGATION.search(sentence):
            continue
        if any(p.search(sentence) for p in UNSAFE_OUTPUT):
            issues.append(f"unsafe statement: {sentence.strip()[:80]}")
    return issues
