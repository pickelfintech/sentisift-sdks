"""Shared pytest fixtures for the SentiSift SDK tests."""
from __future__ import annotations

import pytest

from sentisift import SentiSift

TEST_API_KEY = "sk_sentisift_test_fixture"


@pytest.fixture
def client() -> SentiSift:
    """Return a SentiSift client with a fixed test key and retries disabled.

    Disabling retries keeps tests fast and deterministic when we intentionally
    return transient status codes.
    """
    return SentiSift(api_key=TEST_API_KEY, max_retries=0)


@pytest.fixture
def client_with_retries() -> SentiSift:
    """Return a SentiSift client with a test key and retries enabled."""
    return SentiSift(api_key=TEST_API_KEY, max_retries=3)
