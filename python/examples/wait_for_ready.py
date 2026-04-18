"""Wait for the SentiSift service to be ready before sending traffic.

Useful right after an API service deploy. Models take 10-60 seconds to
load. ``wait_until_ready()`` polls /health and returns when the service
reports ``status="ready"``, or raises if the timeout is exceeded.

Prerequisites:
    pip install sentisift
    export SENTISIFT_API_KEY=sk_sentisift_your_key_here
"""
from sentisift import SentiSift


def main() -> None:
    client = SentiSift()

    health = client.get_health()
    print(f"Initial state: {health.status}")
    if health.progress:
        print(f"  Progress: {health.progress.current}/{health.progress.total} ({health.progress.scorer_name})")

    if health.status != "ready":
        print("Waiting up to 60s for service to become ready...")
        client.wait_until_ready(timeout=60)
        print("Service is ready.")
    else:
        print("Service was already ready. No wait needed.")

    # Now safe to call analyze, get_usage, etc.
    print(f"Balance: {client.get_usage().comment_balance} comments.")


if __name__ == "__main__":
    main()
