# 📱 Spam SMS Classifier

A machine learning system that detects spam SMS messages in real time. Built with a full production stack: trained ML model, REST API, Telegram Bot, and an analytics dashboard.

-----

## 🚀 Features

- **ML Model** — TF-IDF + Naive Bayes classifier with 7 engineered features
- **REST API** — Flask API with single and batch prediction endpoints
- **Telegram Bot** — Real-time spam detection via Telegram
- **Dashboard** — React analytics dashboard with confusion matrix and probability charts
- **Docker** — Fully containerized and production-ready

-----

## 📊 Model Performance

|Metric   |Score|
|---------|-----|
|Accuracy |~98% |
|Precision|100% |
|Recall   |100% |
|F1 Score |100% |


> Validated on 500 synthetic SMS messages

-----

## 🛠️ Tech Stack

|Layer   |Tools                                        |
|--------|---------------------------------------------|
|ML      |Scikit-learn, TF-IDF, Naive Bayes            |
|NLP     |NLTK (tokenization, lemmatization, stopwords)|
|API     |Flask, Gunicorn                              |
|Bot     |python-telegram-bot, httpx                   |
|Frontend|React, Recharts                              |
|DevOps  |Docker                                       |

-----

## 📁 Project Structure

```
sms-spam-classifier/
├── app.py                        # Flask REST API
├── telegram_bot.py               # Telegram Bot
├── Dockerfile                    # Docker image
├── docker-compose.yml            # Docker Compose config
├── requirements.txt              # Python dependencies
├── .dockerignore
├── notebooks/
│   └── spam_classifier_fixed.ipynb   # Model training notebook
├── results/
│   ├── results.json                  # Test results (500 messages)
│   └── results_random_20260612.json  # Random test results
├── images/
│   ├── confusion_matrix.png
│   ├── roc_curves.png
│   ├── pr_curves.png
│   └── radar_chart.png
├── dashboard/
│   └── spam_dashboard.html           # Standalone HTML dashboard
└── README.md
```

-----

## ⚙️ How It Works

1. Raw SMS text is cleaned using NLTK (stop-word removal, lemmatization)
1. Seven numeric features are extracted per message:
- Character length, word count
- Keyword score (spam word matching)
- Caps ratio, exclamation count
- URL presence, phone number presence
1. TF-IDF vectorizes the cleaned text
1. Naive Bayes predicts spam probability
1. A rule-based override catches short high-keyword messages

-----

## 🔌 API Endpoints

### `GET /health`

Returns API status and model load state.

### `POST /predict`

Classify a single SMS message.

```json
{
  "message": "You won a FREE prize! Call now!",
  "threshold": 0.35
}
```

**Response:**

```json
{
  "label": "SPAM",
  "spam_probability": 0.97,
  "threshold": 0.35,
  "rule_triggered": false
}
```

### `POST /predict/batch`

Classify up to 500 messages at once.

```json
{
  "messages": ["Win a free iPhone!", "Hey, are you coming tonight?"],
  "threshold": 0.35
}
```

-----

## 🐳 Run with Docker

```bash
# Build the image
docker build -t spam-classifier .

# Run the API
docker run -p 5000:5000 -v $(pwd)/spam_model.pkl:/app/spam_model.pkl spam-classifier

# Run the Telegram Bot
docker run -e BOT_TOKEN=your_token -e API_URL=http://localhost:5000 spam-classifier python telegram_bot.py
```

-----

## 🤖 Telegram Bot Commands

|Command     |Description                       |
|------------|----------------------------------|
|`/start`    |Show help                         |
|`/health`   |Check API status                  |
|`/threshold`|Adjust spam sensitivity           |
|`/batch`    |Classify multiple messages at once|
|`/cancel`   |Exit batch mode                   |

-----

## 👤 Author

**Mahmoud Shoair**

- LinkedIn: [linkedin.com/in/mahmoud-shoair-60b78926a](https://linkedin.com/in/mahmoud-shoair-60b78926a)
- GitHub: [github.com/mahmoud1-png](https://github.com/mahmoud1-png)
