#!/usr/bin/env python3
"""
test_500_random.py — Generate 500 synthetic random SMS messages and test them
=============================================================================
No CSV needed. Messages are built from realistic templates with randomised
names, amounts, times, etc.  The script produces the same JSON format as
test_500.py so the same spam_dashboard.jsx works for visualisation.

Usage:
    python test_500_random.py
    python test_500_random.py --api-url http://localhost:5000 --n 500 --seed 42
"""

import argparse
import json
import random
import sys
from datetime import datetime

import requests

# ─────────────────────────────────────────────────────────────────────────────
# Vocabulary pools
# ─────────────────────────────────────────────────────────────────────────────

NAMES = [
    "James", "Sarah", "Mike", "Emma", "David", "Lisa", "John", "Anna",
    "Tom", "Kate", "Alex", "Maria", "Chris", "Sophie", "Dan", "Olivia",
    "Sam", "Chloe", "Nick", "Amy", "Luke", "Hannah", "Ryan", "Zoe",
    "Ben", "Ella", "Matt", "Grace", "Jack", "Mia",
]

TIMES = [
    "10am", "2pm", "6pm", "8pm", "noon", "3:30pm", "7pm", "9am",
    "4pm", "11am", "this afternoon", "tonight", "tomorrow morning", "5pm",
]

PLACES = [
    "the office", "Starbucks", "the gym", "home", "the park",
    "the restaurant", "work", "downtown", "the mall", "the station",
    "the cinema", "the pub", "school", "the library", "the cafe",
]

AMOUNTS = [
    "$100", "$500", "$1,000", "$5,000", "$10,000", "$50,000",
    "£200", "€150", "$250", "$750", "£1,000", "$2,500", "€500",
]

NUMBERS = [
    "0800-123-456", "1-800-555-0199", "07700 900123",
    "555-0101", "0044 7911 123456", "1-888-555-0142", "0800-456-789",
]

COMPANIES = [
    "Netflix", "Amazon", "PayPal", "Apple", "Google", "Microsoft",
    "Vodafone", "HSBC", "Barclays", "NatWest", "AT&T", "Verizon",
    "eBay", "Facebook", "Instagram", "Spotify", "Uber",
]

# ─────────────────────────────────────────────────────────────────────────────
# Message templates — HAM (normal everyday messages)
# ─────────────────────────────────────────────────────────────────────────────
HAM_TEMPLATES = [
    "Hey {name}, are you free tonight?",
    "Can you pick up some milk on the way home?",
    "Meeting moved to {time} tomorrow.",
    "Happy birthday! Hope you have a great day 🎂",
    "Are you coming to {name}'s party on Saturday?",
    "Don't forget we have dinner with mum at {time}.",
    "Running 10 mins late, be there soon.",
    "The package arrived! Thanks for sending it.",
    "Can we reschedule our call? Something came up.",
    "Just landed, heading to baggage claim now.",
    "Did you watch the game last night?",
    "Stuck in traffic, might be late to the meeting.",
    "Let me know when you're free to chat.",
    "Good morning! Don't forget your umbrella today.",
    "I'll be at {place} if you want to join.",
    "Thanks for dinner last night, it was lovely.",
    "Quick question — what time does the shop close?",
    "On my way! Be there in about 20 minutes.",
    "Just finished the report, sending it over now.",
    "Kids are asking when you're coming over.",
    "Don't forget to take your keys!",
    "Feeling a bit under the weather today.",
    "The wifi is down again, working from the cafe.",
    "Great news — I got the job!",
    "See you at {time} at {place}.",
    "Call me when you get a chance.",
    "How are you feeling? Better today?",
    "Flight confirmed for Thursday. Can you drop me off?",
    "Got your voicemail, calling you back in 5.",
    "Thanks for covering for me yesterday.",
    "Lunch at {place} at {time}?",
    "Reminder: dentist appointment tomorrow at {time}.",
    "The cat knocked over your plant again, sorry.",
    "Can you grab bread on your way back?",
    "Working late tonight, don't wait up.",
    "Are you still coming this weekend?",
    "Left my charger at yours — any chance you can bring it?",
    "The presentation went really well, thank you!",
    "Happy anniversary! Love you so much ❤️",
    "Just checking in — hope everything is going well.",
    "Congrats on the promotion, well deserved!",
    "Did you get my email about the budget?",
    "The train is delayed again, of course.",
    "Save me a seat, getting coffee first.",
    "Long day today. Looking forward to the weekend.",
    "Dropped the kids off at school, heading in now.",
    "Can you send me the WiFi password again?",
    "Don't forget to feed the dog before you leave.",
    "Just woke up, give me 20 mins.",
    "Mum says dinner is at {time}, don't be late.",
    "Coffee machine is broken again. Nightmare.",
    "We're out of toilet paper! Can you grab some?",
    "The match is on at {time}, coming over?",
    "Car is in the garage until Wednesday.",
    "Birthday card is in the kitchen drawer.",
    "Just got back, had an amazing trip!",
    "Can you proofread this email before I send it?",
    "Lost my keys again, help!",
    "Kids' school play is at {time} on Friday.",
    "Picking up takeaway on the way home — want anything?",
    "Just booked the holiday! So excited.",
    "Anyone fancy a walk later?",
    "{name} says hi by the way.",
    "Heading out now, see you at {place}.",
    "Do you want me to save you some leftovers?",
    "The weather is actually nice today for once!",
    "Just remembered it's bin day — can you put it out?",
    "Hope your interview went well, thinking of you.",
    "Sorry I missed your call, was in a meeting.",
    "Back home safe, thanks for a great evening.",
    "Could you babysit on Friday night? Pretty please 😊",
    "Found your wallet in the car. I'll drop it off.",
    "The kids are in bed. Finally! 😅",
    "Do we need anything from the supermarket?",
    "Caught the earlier train, be home by {time}.",
    "Bit chilly out there today — bring a jacket.",
    "Thanks for the birthday present, you're the best!",
]

# ─────────────────────────────────────────────────────────────────────────────
# Message templates — SPAM (various scam / junk categories)
# ─────────────────────────────────────────────────────────────────────────────
SPAM_TEMPLATES = [
    "CONGRATULATIONS! You've been selected to win {amount}! Reply NOW to claim your prize.",
    "URGENT: Your {company} account has been SUSPENDED. Verify immediately: bit.ly/{code}",
    "FREE gift waiting for you! You've won a prize. Call {number} to claim it now.",
    "Your loan of {amount} has been APPROVED! Click here to receive your funds today.",
    "You have {amount} in unclaimed cashback. Claim before midnight: www.cashback-{code}.com",
    "WINNER! You've won our monthly lottery. Reply with bank details to collect {amount}.",
    "FINAL NOTICE: Your account will be closed. Verify your details NOW at bit.ly/{code}",
    "Exclusive offer: Earn {amount}/month working from home! No experience needed. Apply now.",
    "Your {company} password needs resetting immediately. Click: www.{company}-secure-{code}.com",
    "You qualify for a {amount} government refund. Claim now: www.refund-{code}.net",
    "ALERT: Suspicious login detected on your account. Call {number} IMMEDIATELY.",
    "Congratulations! You've been selected to receive a FREE iPhone. Reply YES to claim.",
    "Get out of debt fast! We can legally write off {amount} of your debt. Call {number}.",
    "Limited time: 90% off all medications. Discreet delivery. Order: pill-{code}.com",
    "You are a WINNER! Claim your {amount} prize by texting WIN to {number}.",
    "Your card has been compromised. Call {number} RIGHT NOW to secure your account.",
    "SPECIAL VIP OFFER: {amount} casino bonus waiting for you. Register: casino-{code}.com",
    "Your credit score qualifies you for a {amount} instant loan. No checks. Apply: loan-{code}.com",
    "IMPORTANT: Your {company} account has been locked. Click now: www.verify-{code}.com",
    "Proven system pays {amount} per day working from home. Start now: earn-{code}.com",
    "FREE entry — you could win {amount}! Visit: www.prize-{code}.com before midnight.",
    "LAST CHANCE: Unclaimed {amount} prize expires in 24 hours. Call {number} NOW.",
    "We need to verify your details or your account closes today. Click: bit.ly/{code}",
    "Tax refund of {amount} is owed to you. Claim here: www.taxrefund-{code}.com",
    "Hot singles near you want to chat. FREE registration: www.meet-{code}.net",
    "You have been chosen for a special {amount} reward. Reply CLAIM to receive it.",
    "Your invoice of {amount} is overdue. To avoid legal action visit: debt-{code}.com",
    "Your exclusive code is PRIZE{code}. Redeem {amount} at: winbig-{code}.net now.",
    "Security breach on your {company} account! Immediate action required. Call {number}.",
    "As a loyal customer you've won {amount}. Click to claim: reward-{code}.net",
    "Double your money fast! Investment opportunity — {amount} return guaranteed. Click here.",
    "Your {company} subscription expires today. Renew now to avoid losing access: {code}.net",
    "SIX FIGURE INCOME from home! {name} made {amount} last month. Find out how: rich-{code}.com",
    "You've been pre-approved for a {amount} credit limit increase. Activate: card-{code}.com",
    "BREAKING: Claim your {amount} stimulus payment before the deadline: gov-{code}.com",
    "Explicit content unlocked! View your free videos now at: adult-{code}.net",
    "Win {amount} every week! Join our free lottery at: lottery-{code}.com — no purchase needed",
    "Your parcel could not be delivered. Pay {amount} redelivery fee: parcel-{code}.com",
    "Urgent: {company} billing issue — your service will be suspended. Fix now: bill-{code}.net",
    "Lose weight FAST — guaranteed! Our secret pill costs only $19.99. Order: slim-{code}.com",
]


# ─────────────────────────────────────────────────────────────────────────────
# Generator helpers
# ─────────────────────────────────────────────────────────────────────────────

def gen_code() -> str:
    return "".join(random.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=6))


def fill(template: str) -> str:
    """Substitute all {placeholders} with random values."""
    return (
        template
        .replace("{name}",    random.choice(NAMES))
        .replace("{time}",    random.choice(TIMES))
        .replace("{place}",   random.choice(PLACES))
        .replace("{amount}",  random.choice(AMOUNTS))
        .replace("{number}",  random.choice(NUMBERS))
        .replace("{company}", random.choice(COMPANIES))
        .replace("{code}",    gen_code())
    )


def generate(n: int, seed: int) -> list:
    """Return n message dicts with 'text' and 'true_label', shuffled."""
    random.seed(seed)
    n_spam = n // 2
    n_ham  = n - n_spam

    msgs = []
    for _ in range(n_ham):
        msgs.append({"text": fill(random.choice(HAM_TEMPLATES)),  "true_label": "ham"})
    for _ in range(n_spam):
        msgs.append({"text": fill(random.choice(SPAM_TEMPLATES)), "true_label": "spam"})

    random.shuffle(msgs)
    return msgs


# ─────────────────────────────────────────────────────────────────────────────
# API caller
# ─────────────────────────────────────────────────────────────────────────────

def run_batch(messages: list, api_url: str, threshold: float) -> list:
    BATCH, out = 500, []
    for i in range(0, len(messages), BATCH):
        chunk = [m["text"] for m in messages[i : i + BATCH]]
        print(f"  Sending messages {i + 1}–{i + len(chunk)}…")
        resp = requests.post(
            f"{api_url}/predict/batch",
            json={"messages": chunk, "threshold": threshold},
            timeout=120,
        )
        resp.raise_for_status()
        out.extend(resp.json()["results"])
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Metrics
# ─────────────────────────────────────────────────────────────────────────────

def compute_metrics(rows: list) -> dict:
    tp = sum(1 for r in rows if r["true_label"] == "spam" and r["predicted_label"] == "SPAM")
    tn = sum(1 for r in rows if r["true_label"] == "ham"  and r["predicted_label"] == "HAM")
    fp = sum(1 for r in rows if r["true_label"] == "ham"  and r["predicted_label"] == "SPAM")
    fn = sum(1 for r in rows if r["true_label"] == "spam" and r["predicted_label"] == "HAM")
    total     = tp + tn + fp + fn
    accuracy  = (tp + tn) / total                          if total             else 0
    precision = tp / (tp + fp)                             if (tp + fp)         else 0
    recall    = tp / (tp + fn)                             if (tp + fn)         else 0
    f1        = 2 * precision * recall / (precision + recall) if (precision + recall) else 0
    return dict(
        accuracy=round(accuracy, 4),  precision=round(precision, 4),
        recall=round(recall, 4),      f1=round(f1, 4),
        true_positives=tp,  true_negatives=tn,
        false_positives=fp, false_negatives=fn,
        total=total, spam_total=tp + fn, ham_total=tn + fp,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="Test 500 synthetic random SMS messages against the spam classifier")
    ap.add_argument("--api-url",   default="http://localhost:5000", help="Base URL of the Flask API")
    ap.add_argument("--n",         type=int,   default=500,         help="Number of messages to generate")
    ap.add_argument("--threshold", type=float, default=0.35,        help="Decision threshold (0–1)")
    ap.add_argument("--seed",      type=int,   default=42,          help="Random seed (change to get different messages)")
    ap.add_argument("--output",    default=None,                    help="Output JSON filename (auto-named if omitted)")
    args = ap.parse_args()

    # 1. Generate
    print(f"\n🎲  Generating {args.n} random SMS messages (seed={args.seed})…")
    msgs       = generate(args.n, args.seed)
    spam_count = sum(1 for m in msgs if m["true_label"] == "spam")
    ham_count  = len(msgs) - spam_count
    print(f"    Generated: {spam_count} spam  |  {ham_count} ham")

    # 2. Health check
    print(f"\n🔌  Checking API at {args.api_url}/health…")
    try:
        h = requests.get(f"{args.api_url}/health", timeout=5).json()
        print(f"    Status: {h.get('status')}  |  Model loaded: {h.get('model_loaded')}")
    except Exception as exc:
        sys.exit(f"ERROR: Cannot reach API — {exc}\nMake sure 'docker compose up' is running.")

    # 3. Classify
    print(f"\n⚡  Classifying {len(msgs)} messages (threshold={args.threshold})…")
    api_rows = run_batch(msgs, args.api_url, args.threshold)

    # 4. Merge results
    results = []
    for idx, (msg, api) in enumerate(zip(msgs, api_rows)):
        results.append({
            "index":            idx,
            "text":             msg["text"],
            "true_label":       msg["true_label"],
            "predicted_label":  api["label"],
            "spam_probability": api["spam_probability"],
            "threshold":        api["threshold"],
            "rule_triggered":   api.get("rule_triggered", False),
            "correct":          msg["true_label"].upper() == api["label"],
        })

    # 5. Compute metrics + save
    metrics  = compute_metrics(results)
    out_path = args.output or f"results_random_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "tested_at": datetime.now().isoformat(),
            "api_url":   args.api_url,
            "threshold": args.threshold,
            "seed":      args.seed,
            "total":     len(results),
            "source":    "synthetic_random",
            "metrics":   metrics,
            "results":   results,
        }, f, indent=2, ensure_ascii=False)

    # 6. Print summary
    m = metrics
    print(f"\n{'='*55}")
    print(f"  Results saved → {out_path}")
    print(f"{'='*55}")
    print(f"  Accuracy:  {m['accuracy']:.1%}   ({m['true_positives']+m['true_negatives']}/{m['total']} correct)")
    print(f"  Precision: {m['precision']:.1%}   ({m['false_positives']} false alarms)")
    print(f"  Recall:    {m['recall']:.1%}   ({m['false_negatives']} spam missed)")
    print(f"  F1 Score:  {m['f1']:.1%}")
    print(f"  TP={m['true_positives']}  TN={m['true_negatives']}  "
          f"FP={m['false_positives']}  FN={m['false_negatives']}")
    print(f"{'='*55}")
    print(f"\n  Load {out_path} into spam_dashboard.jsx to view the full dashboard.\n")


if __name__ == "__main__":
    main()
