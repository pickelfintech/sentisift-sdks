"""Minimal SentiSift quickstart.

Prerequisites:
    pip install sentisift
    export SENTISIFT_API_KEY=sk_sentisift_your_key_here

Run:
    python quickstart.py

Sends three comments for a fake article and prints the result. Shows the
two response shapes (`buffered` while collecting, `processed` once the
batch crosses the per-article threshold) and a balance check.
"""
from sentisift import SentiSift


def main() -> None:
    client = SentiSift()  # reads SENTISIFT_API_KEY from env

    result = client.analyze(
        article_url="https://example.com/article/quickstart",
        article_text="The article body. Send this on the FIRST batch only.",
        title="Quickstart Article",
        comments=[
            {"text": "Great points, well argued.", "author": "alice", "time": "2026-04-18T10:00:00", "likes": 12},
            {"text": "I disagree, here's why...", "author": "bob", "time": "2026-04-18T10:05:00", "likes": 3, "dislikes": 1},
            {"text": "Buy crypto-coin-x at 10x leverage now!", "author": "user_29481", "time": "2026-04-18T10:07:00"},
        ],
    )

    if result.status == "buffered":
        print(f"Buffered: {result.buffered_count}/{result.threshold} comments not yet analyzed.")
        print("Send more batches for this article and the buffer will eventually flip to 'processed'.")
    else:
        print(f"Processed {len(result.comments)} comments:\n")
        for c in result.comments:
            tag = " [SentiSift]" if c.is_influence else ""
            print(f"  [{c.sentiment_label:<10}] {c.text}{tag}")
        print(f"\nModeration: {result.moderation.total_approved} approved, {result.moderation.total_removed} removed.")
        print(f"Balance after this call: {result.comment_balance} comments remaining.")

    print(f"\nLifetime balance: {client.get_usage().comment_balance} comments.")


if __name__ == "__main__":
    main()
