from vaahan.rate_limit import SlidingWindowLimiter


def test_limiter_rejects_after_limit() -> None:
    limiter = SlidingWindowLimiter(limit=2)
    assert limiter.allow("client")
    assert limiter.allow("client")
    assert not limiter.allow("client")
