from __future__ import annotations

import unicodedata
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Intent(StrEnum):
    COMPLAINT = "complaint"
    ORDER_INQUIRY = "order_inquiry"
    REFUND_REQUEST = "refund_request"
    PRAISE = "praise"
    NEGOTIATING = "negotiating"
    SPAM = "spam"
    OUT_OF_DOMAIN = "out_of_domain"


class Category(StrEnum):
    ORDERS = "orders"
    REFUNDS = "refunds"
    PAYMENTS = "payments"
    PRODUCTS = "products"
    RETURNS = "returns"
    ACCOUNT = "account"
    OFFERS = "offers"
    SPAM = "spam"
    OOD = "ood"


class IssueType(StrEnum):
    ORDER_STATUS = "order_status"
    DELIVERY_DELAYED = "delivery_delayed"
    ORDER_CANCELLED = "order_cancelled"
    WRONG_ADDRESS = "wrong_address"
    TRACK_PACKAGE = "track_package"
    EXPECTED_DELIVERY = "expected_delivery"
    REFUND_STATUS = "refund_status"
    REFUND_FAILED = "refund_failed"
    MONEY_NOT_CREDITED = "money_not_credited"
    REFUND_PENDING = "refund_pending"
    PARTIAL_REFUND = "partial_refund"
    WALLET_ISSUE = "wallet_issue"
    PAYMENT_TIMEOUT = "payment_timeout"
    COD_ISSUE = "cod_issue"
    EMI_ISSUE = "emi_issue"
    CARD_CHARGED_TWICE = "card_charged_twice"
    UPI_FAILED = "upi_failed"
    WARRANTY_ISSUE = "warranty_issue"
    PRODUCT_DEFECTIVE = "product_defective"
    INSTALLATION_ISSUE = "installation_issue"
    FAKE_PRODUCT = "fake_product"
    MISSING_ACCESSORIES = "missing_accessories"
    EXCHANGE_REQUEST = "exchange_request"
    REPLACEMENT_REQUEST = "replacement_request"
    RETURN_PICKUP = "return_pickup"
    DAMAGED_PRODUCT = "damaged_product"
    WRONG_SIZE = "wrong_size"
    ADDRESS_UPDATE = "address_update"
    PHONE_NUMBER_UPDATE = "phone_number_update"
    PROFILE_UPDATE = "profile_update"
    LOGIN_ISSUE = "login_issue"
    OTP_ISSUE = "otp_issue"
    EMAIL_UPDATE = "email_update"
    CASHBACK_ISSUE = "cashback_issue"
    NEGOTIATION = "negotiation"
    DISCOUNT_REQUEST = "discount_request"
    COUPON_REQUEST = "coupon_request"
    PRICE_MATCH = "price_match"
    TRANSLATE_REQUEST = "translate_request"
    SPORTS_SCORE = "sports_score"
    RECIPE_QUERY = "recipe_query"
    JOKE_REQUEST = "joke_request"
    WEATHER_QUERY = "weather_query"
    EARN_MONEY = "earn_money"
    CLICK_LINK = "click_link"
    CALL_NOW = "call_now"


class Urgency(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Sentiment(StrEnum):
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    POSITIVE = "positive"


class LanguageMix(StrEnum):
    HINDI_DOMINANT = "hindi_dominant"
    ENGLISH_DOMINANT = "english_dominant"
    BALANCED = "balanced"


class PaymentMethod(StrEnum):
    UPI = "upi"
    WALLET = "wallet"
    CARD = "card"
    EMI = "emi"
    COD = "cod"
    NETBANKING = "netbanking"


class Resolution(StrEnum):
    NONE = "none"
    INFORMATION = "information"
    REPLACEMENT = "replacement"
    STATUS_UPDATE = "status_update"
    REFUND = "refund"
    DISCOUNT = "discount"


class SetuOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent: Intent
    category: Category | None
    issue_type: IssueType | None
    urgency: Urgency
    sentiment: Sentiment
    language_mix: LanguageMix
    order_id: str | None
    product_name: str | None
    payment_method: PaymentMethod | None
    resolution_requested: Resolution

    @field_validator("issue_type", "order_id", "product_name", mode="before")
    @classmethod
    def clean_optional_text(cls, value: Any) -> Any:
        if value is None or not isinstance(value, str):
            return value
        cleaned = unicodedata.normalize("NFKC", value).strip()
        return cleaned or None

    @model_validator(mode="after")
    def validate_hierarchy(self) -> SetuOutput:
        if self.intent == Intent.SPAM and self.category != Category.SPAM:
            raise ValueError("spam intent requires spam category")
        if self.intent == Intent.OUT_OF_DOMAIN and self.category != Category.OOD:
            raise ValueError("out_of_domain intent requires ood category")
        if self.intent in {Intent.SPAM, Intent.OUT_OF_DOMAIN} and any(
            (self.order_id, self.product_name, self.payment_method)
        ):
            raise ValueError("non-commerce inputs cannot contain commerce entities")
        return self


class AnalyzeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=3, max_length=600)
    request_id: str | None = Field(default=None, min_length=8, max_length=80)

    @field_validator("message")
    @classmethod
    def normalize_message(cls, value: str) -> str:
        value = unicodedata.normalize("NFKC", value).strip()
        if len(value) < 3:
            raise ValueError("message must contain at least three visible characters")
        return value


class ResponseMetadata(BaseModel):
    request_id: str
    release: str
    model: str
    quantization: str
    schema_version: str
    prompt_version: str
    latency_ms: float


class AnalyzeResponse(BaseModel):
    result: SetuOutput
    metadata: ResponseMetadata


class ErrorBody(BaseModel):
    code: str
    message: str
    request_id: str
