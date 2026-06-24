# ─────────────────────────────────────────────────────────────────────────────
# Spam Classifier — single image for both the Flask API and the Telegram bot.
#
# Build:   docker build -t spam-classifier .
# Run API: docker run -p 5000:5000 -v $(pwd)/spam_model.pkl:/app/spam_model.pkl spam-classifier
# Run bot: docker run -e BOT_TOKEN=<token> -e API_URL=http://<api-host>:5000 \
#                    spam-classifier python telegram_bot.py
#
# Or use docker-compose (recommended): see docker-compose.yml
# ─────────────────────────────────────────────────────────────────────────────

FROM python:3.11-slim

# ── System dependencies ───────────────────────────────────────────────────────
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        gcc \
        curl \
 && rm -rf /var/lib/apt/lists/*

# ── Non-root user ─────────────────────────────────────────────────────────────
# Running as root gives a compromised process full container privileges.
# A dedicated unprivileged user limits the blast radius of any exploit.
# --create-home gives gunicorn a writable home dir for its control socket.
RUN groupadd --gid 1001 appgroup \
 && useradd  --uid 1001 --gid appgroup --create-home appuser

# ── Working directory ─────────────────────────────────────────────────────────
WORKDIR /app

# ── Python dependencies (layer-cached unless requirements.txt changes) ────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── NLTK corpora (downloaded once into a system-wide, world-readable path) ────
# FIX: Previously downloaded as root into /root/nltk_data, which appuser
# cannot read at runtime.  Writing to /usr/local/share/nltk_data puts the data
# in NLTK's default search path and makes it accessible to every user.
ENV NLTK_DATA=/usr/local/share/nltk_data
RUN python - <<'EOF'
import nltk, os
os.makedirs("/usr/local/share/nltk_data", exist_ok=True)
for pkg in ("punkt", "punkt_tab", "stopwords", "wordnet"):
    nltk.download(pkg, download_dir="/usr/local/share/nltk_data", quiet=True)
EOF

# ── Application source ────────────────────────────────────────────────────────
COPY app.py telegram_bot.py ./

# ── Ownership ─────────────────────────────────────────────────────────────────
RUN chown -R appuser:appgroup /app
USER appuser

# ── Runtime configuration ─────────────────────────────────────────────────────
ENV MODEL_PATH=/app/spam_model.pkl \
    THRESHOLD=0.35 \
    PORT=5000 \
    MAX_MSG_LEN=2000

EXPOSE 5000

# ── Health-check (API only) ───────────────────────────────────────────────────
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -sf http://localhost:${PORT}/health || exit 1

# ── Default command: Flask API via Gunicorn ───────────────────────────────────
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "60", "app:app"]