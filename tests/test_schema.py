from __future__ import annotations

import pytest
from pydantic import ValidationError

from vaahan.schema import AnalyzeRequest, SetuOutput


def test_request_normalizes_unicode_and_space() -> None:
    request = AnalyzeRequest(message="  UPI issue hai  ")
    assert request.message == "UPI issue hai"


def test_output_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        SetuOutput.model_validate(
            {
                "intent": "complaint",
                "category": "payments",
                "issue_type": "upi_failed",
                "urgency": "low",
                "sentiment": "negative",
                "language_mix": "balanced",
                "order_id": None,
                "product_name": None,
                "payment_method": "upi",
                "resolution_requested": "information",
                "confidence": 0.9,
            }
        )


def test_out_of_domain_cannot_extract_commerce_entity() -> None:
    with pytest.raises(ValidationError):
        SetuOutput.model_validate(
            {
                "intent": "out_of_domain",
                "category": "ood",
                "issue_type": "weather_query",
                "urgency": "low",
                "sentiment": "neutral",
                "language_mix": "balanced",
                "order_id": "ORD123",
                "product_name": None,
                "payment_method": None,
                "resolution_requested": "none",
            }
        )
