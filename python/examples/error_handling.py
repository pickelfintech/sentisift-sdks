"""SentiSift error handling - one example per typed exception.

Demonstrates the typed exception hierarchy and how to read the deep-link
``docs_url`` and correlation ``request_id`` for self-service debugging.

Each scenario is contrived (missing field, bad key, etc.) so you can see
what each exception looks like without breaking your live integration.

Prerequisites:
    pip install sentisift
    export SENTISIFT_API_KEY=sk_sentisift_your_key_here

Run:
    python error_handling.py
"""
from sentisift import (
    SentiSift,
    SentiSiftAuthError,
    SentiSiftError,
    SentiSiftRateLimitError,
    SentiSiftServerError,
    SentiSiftServiceLoadingError,
    SentiSiftValidationError,
)


def show(label: str, fn) -> None:
    print(f"\n--- {label} ---")
    try:
        fn()
        print("(no exception raised)")
    except SentiSiftValidationError as err:
        # Validation errors include a deep-linked docs_url that targets the
        # exact field row in the HTML docs (e.g. #request-format-comment-author).
        print(f"validation: {err}")
        print(f"  docs_url:   {err.docs_url}")
        print(f"  request_id: {err.request_id}")
    except SentiSiftAuthError as err:
        print(f"auth: {err}  (docs_url={err.docs_url})")
    except SentiSiftRateLimitError as err:
        # 429 rate-limit. Exception is only raised after retries exhaust.
        # In normal use the SDK auto-retries respecting Retry-After.
        print(f"rate-limit: {err}  (retry_after={err.retry_after}s)")
    except SentiSiftServiceLoadingError as err:
        # 503 - models loading after a deploy. SDK auto-retries; if you
        # see this exception, retries exhausted. Wait 30-60s and retry.
        print(f"service-loading: {err}")
    except SentiSiftServerError as err:
        print(f"server (5xx): {err}  (request_id={err.request_id})")
    except SentiSiftError as err:
        print(f"unexpected SentiSift error: {err}")


def main() -> None:
    valid_client = SentiSift()  # uses SENTISIFT_API_KEY env var
    bad_client = SentiSift(api_key="sk_sentisift_obviously_invalid_key_for_demo_only")

    # Validation: missing required `author` field on the comment.
    show(
        "Validation - missing comment.author",
        lambda: valid_client.analyze(
            article_url="https://example.com/article/err-demo",
            comments=[{"text": "hi", "time": "2026-04-18T10:00:00"}],
        ),
    )

    # Validation: missing required `metadata.article_url`.
    show(
        "Validation - missing metadata.article_url",
        lambda: valid_client.analyze(
            article_url="",
            comments=[{"text": "hi", "author": "x", "time": "2026-04-18T10:00:00"}],
        ),
    )

    # Auth: wrong key.
    show(
        "Auth - invalid key",
        lambda: bad_client.get_usage(),
    )


if __name__ == "__main__":
    main()
