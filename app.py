"""
app.py — Spam Classifier REST API
──────────────────────────────────
Endpoints:
  GET  /health          → liveness / readiness probe
  POST /predict         → classify a single message
  POST /predict/batch   → classify a list of messages
"""

import os
import re
import pickle
import logging

import pandas as pd
from flask import Flask, request, jsonify

from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# ── Config from environment ───────────────────────────────────────────────────
MODEL_PATH  = os.getenv("MODEL_PATH", "spam_model.pkl")
MAKE_DF_PATH = os.getenv("MAKE_DF_PATH", "make_df.pkl")
MAX_MSG_LEN = int(os.getenv("MAX_MSG_LEN", "2000"))

try:
    THRESHOLD = float(os.getenv("THRESHOLD", "0.35"))
    if not (0.0 < THRESHOLD < 1.0):
        raise ValueError("out of (0, 1) range")
except ValueError:
    log.warning("Invalid THRESHOLD env var — defaulting to 0.35")
    THRESHOLD = 0.35

# ── NLP helpers (must match training notebook exactly) ────────────────────────
stop_words = set(stopwords.words("english"))
lemmatizer = WordNetLemmatizer()

NUM_FEATURES = [
    "char_len", "word_count", "keyword_score",
    "caps_ratio", "exclamation_count", "has_url", "has_phone",
]

SPAM_WORDS = {
    "free", "win", "winner", "won", "prize", "award", "gift",
    "reward", "bonus", "jackpot", "lottery", "sweepstake", "congratulations",
    "selected", "chosen", "lucky", "giveaway",
    "cash", "money", "dollar", "pounds", "euro", "salary", "income",
    "profit", "earn", "earning", "investment", "loan", "credit", "debt",
    "mortgage", "insurance", "refund", "voucher", "discount", "coupon",
    "deal", "offer", "save", "saving",
    "urgent", "immediately", "instant", "now", "today", "tonight",
    "hurry", "rush", "limited", "expire", "deadline", "final", "last",
    "warning", "alert", "attention", "important", "critical", "act",
    "account", "password", "login", "verify", "verification", "confirm",
    "suspended", "blocked", "compromised", "unauthorized", "security",
    "update", "information", "details", "click", "link", "access",
    "validate", "authenticate",
    "call", "contact", "reply", "text", "sms", "phone", "mobile",
    "number", "toll", "helpline", "customer", "service", "support",
    "sex", "adult", "xxx", "dating", "single", "meet", "hot",
    "horny", "explicit", "nude",
    "subscribe", "subscription", "trial", "cancel", "charge",
    "billing", "invoice", "receipt", "order", "delivery",
    "claim", "guaranteed", "promise", "100", "percent", "risk",
    "opportunity", "exclusive", "special", "vip", "member", "membership",
    # BUG FIX: The 13 words below were added in app.py but were NOT in the
    # training notebook's SPAM_WORDS set.  They inflate keyword_score at
    # inference, causing the rule-based override to fire on innocent messages
    # (e.g. "Earn passive income with zero effort" → wrongly flagged SPAM).
    # Removed to match training exactly.
    # Removed: fast, daily, proven, system, passive, zero,
    #          meds, prescription, online, medication, trick, simple, hack
}

# ── Pre-compiled regex patterns (compiled once, reused on every call) ─────────
# FIX 7: Compiling inside helper functions wastes CPU on every request.
#         All patterns are now module-level constants.
_RE_ALPHA      = re.compile(r"[^a-zA-Z]")
_RE_URL        = re.compile(r"http|www\.|\.com|\.net|\.org", re.IGNORECASE)
# BUG FIX: Training notebook used: r'\b\d{5,}\b|\(\d{3}\)'
# This matches any 5+ digit run (e.g. "80086", "12345") or a bracketed area
# code "(555)". The old app.py used a sophisticated formatted-number pattern
# that missed all of those, causing has_phone=0 where training saw has_phone=1.
# Must use the exact training regex to avoid train/serve skew.
_RE_PHONE      = re.compile(r"\b\d{5,}\b|\(\d{3}\)")

# ── Rule-based override ───────────────────────────────────────────────────────
RULE_MIN_KEYWORDS = int(os.getenv("RULE_MIN_KEYWORDS", "2"))
RULE_MAX_WORDS    = int(os.getenv("RULE_MAX_WORDS", "15"))

# Minimum model probability required before the keyword rule may override the
# label to SPAM.  Prevents the rule from overruling a confident HAM prediction
# (e.g. "I'll call you later tonight." scores 5 % — well below this floor).
try:
    RULE_MIN_PROB = float(os.getenv("RULE_MIN_PROB", "0.20"))
    if not (0.0 <= RULE_MIN_PROB < 1.0):
        raise ValueError("out of [0, 1) range")
except ValueError:
    log.warning("Invalid RULE_MIN_PROB env var — defaulting to 0.20")
    RULE_MIN_PROB = 0.20


def rule_check(text: str) -> bool:
    """Return True if the keyword/length heuristics flag this message."""
    return (keyword_score(text) >= RULE_MIN_KEYWORDS
            and len(text.split()) <= RULE_MAX_WORDS)


def preprocess(text: str) -> str:
    tokens = _RE_ALPHA.sub(" ", text).lower().split()
    tokens = [lemmatizer.lemmatize(w) for w in tokens if w not in stop_words]
    return " ".join(tokens)


def keyword_score(text: str) -> int:
    tokens = set(_RE_ALPHA.sub(" ", text).lower().split())
    return sum(1 for w in SPAM_WORDS if w in tokens)


def caps_ratio(text: str) -> float:
    letters = [c for c in text if c.isalpha()]
    return sum(1 for c in letters if c.isupper()) / len(letters) if letters else 0.0


def exclamation_count(text: str) -> int:
    return text.count("!")


def has_url(text: str) -> int:
    return int(bool(_RE_URL.search(text)))


def has_phone(text: str) -> int:
    return int(bool(_RE_PHONE.search(text)))


def build_row(text: str) -> pd.DataFrame:
    """Convert a raw SMS string into the feature DataFrame the model expects."""
    clean = preprocess(text)
    # BUG FIX: char_len and word_count must be measured on the *cleaned* text,
    # exactly as done during training (notebook cell 4):
    #   data['char_len']  = data['Clean_Text'].apply(len)
    #   data['word_count'] = data['Clean_Text'].apply(lambda x: len(x.split()))
    # Using raw text here caused systematically wrong values at inference.
    return pd.DataFrame([[
        clean,
        len(clean),
        len(clean.split()),
        keyword_score(text),
        caps_ratio(text),
        exclamation_count(text),
        has_url(text),
        has_phone(text),
    ]], columns=["text"] + NUM_FEATURES)


# ── Load model ────────────────────────────────────────────────────────────────
def load_model(path: str):
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        log.warning("Model file '%s' not found or empty — predictions will fail.", path)
        return None
    with open(path, "rb") as f:
        model = pickle.load(f)
    log.info("Model loaded from '%s'.", path)
    return model


def load_make_df(path: str):
    """Load the optional make_df preprocessor pipeline if present.

    make_df.pkl is produced by the training notebook where the helper function
    is defined in __main__.  When gunicorn imports app.py as a module that
    context no longer exists, so pickle raises AttributeError.  We catch it
    and fall back gracefully — the model pipeline is self-contained and does
    not need this file at inference time.
    """
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        log.info("make_df file '%s' not found — assuming pipeline is self-contained in model.", path)
        return None
    try:
        with open(path, "rb") as f:
            make_df = pickle.load(f)
        log.info("make_df preprocessor loaded from '%s'.", path)
        return make_df
    except AttributeError as exc:
        log.warning(
            "Could not unpickle '%s': %s. "
            "This is expected when make_df was defined in a notebook __main__ scope. "
            "Inference will use the self-contained model pipeline.",
            path, exc,
        )
        return None
    except Exception as exc:
        log.warning("Unexpected error loading make_df from '%s': %s. Skipping.", path, exc)
        return None


model   = load_model(MODEL_PATH)
make_df = load_make_df(MAKE_DF_PATH)

# ── Flask app ─────────────────────────────────────────────────────────────────
app = Flask(__name__)


def _validate_threshold(value: float) -> tuple[bool, str]:
    """Return (ok, error_message). Validates threshold is within (0, 1)."""
    if not (0.0 < value < 1.0):
        return False, f"'threshold' must be between 0 and 1 (exclusive), got {value}."
    return True, ""


def classify(text: str, threshold: float = THRESHOLD) -> dict:
    if model is None:
        raise RuntimeError("Model not loaded. Mount spam_model.pkl and restart.")

    # Always run the model first so the rule can never override a confident HAM.
    # The rule may only escalate to SPAM when the model already agrees the
    # message leans spammy (prob >= RULE_MIN_PROB).
    row  = build_row(text)
    prob = float(model.predict_proba(row)[0, 1])

    triggered = rule_check(text) and prob >= RULE_MIN_PROB
    label     = "SPAM" if (triggered or prob >= threshold) else "HAM"

    return {"label":            label,
            "spam_probability": round(prob, 4),
            "threshold":        threshold,
            "rule_triggered":   triggered}


def classify_batch(texts: list, threshold: float = THRESHOLD) -> list:
    if model is None:
        raise RuntimeError("Model not loaded. Mount spam_model.pkl and restart.")

    rows  = pd.concat([build_row(t) for t in texts], ignore_index=True)
    probs = model.predict_proba(rows)[:, 1]

    results = []
    for t, p in zip(texts, probs):
        p         = float(p)
        triggered = rule_check(t) and p >= RULE_MIN_PROB
        label     = "SPAM" if (triggered or p >= threshold) else "HAM"
        results.append({
            "label":            label,
            "spam_probability": round(p, 4),
            "threshold":        threshold,
            "rule_triggered":   triggered,
        })
    return results


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status":        "ok",
        "model_loaded":  model is not None,
        "make_df_loaded": make_df is not None,
        "threshold":     THRESHOLD,
    }), 200


@app.route("/predict", methods=["POST"])
def predict():
    body = request.get_json(silent=True)
    if not body or "message" not in body:
        return jsonify({"error": "JSON body must contain a 'message' field."}), 400

    text = str(body["message"]).strip()

    # FIX 8: Reject blank messages before any NLP work.
    if not text:
        return jsonify({"error": "Message must not be empty or whitespace only."}), 400

    if len(text) > MAX_MSG_LEN:
        return jsonify({"error": f"Message exceeds {MAX_MSG_LEN} character limit."}), 400

    # FIX 2: Validate caller-supplied threshold is within (0, 1).
    try:
        threshold = float(body.get("threshold", THRESHOLD))
    except (TypeError, ValueError):
        return jsonify({"error": "'threshold' must be a number."}), 400
    ok, err = _validate_threshold(threshold)
    if not ok:
        return jsonify({"error": err}), 400

    # FIX 3: Catch any unexpected exception and return JSON, not an HTML 500.
    try:
        result = classify(text, threshold)
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 503
    except Exception as exc:
        log.exception("Unexpected error during classification")
        return jsonify({"error": "Internal classification error.", "detail": str(exc)}), 500

    return jsonify({"input": text, **result}), 200


@app.route("/predict/batch", methods=["POST"])
def predict_batch():
    body = request.get_json(force=True, silent=True)
    if not body or "messages" not in body:
        return jsonify({"error": "JSON body must contain a 'messages' list."}), 400

    messages = body["messages"]

    if not isinstance(messages, list) or len(messages) == 0:
        return jsonify({"error": "'messages' must be a non-empty list."}), 400
    if len(messages) > 500:
        return jsonify({"error": "Batch size limited to 500 messages."}), 400

    # FIX 2: Validate caller-supplied threshold.
    try:
        threshold = float(body.get("threshold", THRESHOLD))
    except (TypeError, ValueError):
        return jsonify({"error": "'threshold' must be a number."}), 400
    ok, err = _validate_threshold(threshold)
    if not ok:
        return jsonify({"error": err}), 400

    texts = [str(m).strip() for m in messages]

    # FIX 8: Reject blank messages in the batch.
    blank = [i for i, t in enumerate(texts) if not t]
    if blank:
        return jsonify({"error": f"Messages at indices {blank} are empty or whitespace only."}), 400

    oversized = [i for i, t in enumerate(texts) if len(t) > MAX_MSG_LEN]
    if oversized:
        return jsonify({
            "error": f"Messages at indices {oversized} exceed the "
                     f"{MAX_MSG_LEN} character limit."
        }), 400

    # FIX 3: Catch unexpected exceptions and return JSON.
    try:
        preds = classify_batch(texts, threshold)
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 503
    except Exception as exc:
        log.exception("Unexpected error during batch classification")
        return jsonify({"error": "Internal classification error.", "detail": str(exc)}), 500

    results    = [{"input": t, **p} for t, p in zip(texts, preds)]
    spam_count = sum(1 for r in results if r["label"] == "SPAM")

    return jsonify({
        "count":      len(results),
        "spam_count": spam_count,
        "ham_count":  len(results) - spam_count,
        "results":    results,
    }), 200


if __name__ == "__main__":
    port  = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)