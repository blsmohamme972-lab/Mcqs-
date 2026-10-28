"""Generate golden test vectors for the Kotlin FSRS port from py-fsrs (pip install fsrs==6.3.2).

Usage: python3 tools/gen_fsrs_vectors.py android/app/src/test/resources/fsrs_vectors.json
"""
import json
import random
import sys
from datetime import datetime, timedelta, timezone

from fsrs import Card, Rating, Scheduler

EPOCH = datetime(2026, 1, 1, tzinfo=timezone.utc)
# Gaps chosen to hit every branch: same-day (short-term), learning steps, multi-day reviews.
GAPS = [timedelta(seconds=30), timedelta(minutes=1), timedelta(minutes=5), timedelta(minutes=10),
        timedelta(hours=3), timedelta(hours=23, minutes=59), timedelta(days=1), timedelta(days=2),
        timedelta(days=5), timedelta(days=13), timedelta(days=40), timedelta(days=200)]


def ms(dt):
    return int((dt - EPOCH).total_seconds() * 1000)


def main(out):
    rng = random.Random(20261028)
    configs = [
        Scheduler(enable_fuzzing=False),
        Scheduler(enable_fuzzing=False, desired_retention=0.85,
                  learning_steps=(timedelta(minutes=1),), relearning_steps=()),
        Scheduler(enable_fuzzing=False, learning_steps=(), relearning_steps=(timedelta(minutes=5), timedelta(minutes=30)),
                  maximum_interval=180),
    ]
    cases = []
    for ci, sch in enumerate(configs):
        for _ in range(60):
            card = Card(card_id=1, due=EPOCH)
            t = EPOCH
            steps = []
            for _ in range(rng.randint(1, 14)):
                # Usually review at the due time (+ a gap mix), sometimes early or late.
                choice = rng.random()
                if choice < 0.5:
                    t = max(t, card.due)
                else:
                    t = t + rng.choice(GAPS)
                rating = rng.choice([1, 2, 3, 3, 3, 4])
                card, _ = sch.review_card(card, Rating(rating), review_datetime=t)
                steps.append({
                    "t": ms(t), "rating": rating,
                    "state": int(card.state), "step": card.step,
                    "stability": card.stability, "difficulty": card.difficulty,
                    "due": ms(card.due),
                })
            cases.append({"config": ci, "steps": steps})
    cfg = [{**s.to_dict()} for s in configs]
    with open(out, "w") as f:
        json.dump({"configs": cfg, "cases": cases}, f)
    print(f"wrote {len(cases)} cases, {sum(len(c['steps']) for c in cases)} reviews")


if __name__ == "__main__":
    main(sys.argv[1])
