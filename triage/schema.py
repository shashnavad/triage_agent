from typing import Literal

from pydantic import BaseModel, Field

FIELDS = ["category", "priority", "product_area", "deflectable"]


class Taxonomy(BaseModel):
    reasoning: str = Field(description="Two sentences max: why these values, and whether the KB fully answers it.")
    category: Literal[
        "how_to_question", "bug_defect", "data_issue", "access_account",
        "billing_contract", "feature_request", "security_privacy", "other",
    ]
    priority: Literal["P0", "P1", "P2", "P3"] = Field(description="Based on business impact, never tone.")
    product_area: Literal[
        "account_admin", "invoicing", "payments", "bank_feeds",
        "data_import", "reports_exports", "api_webhooks", "general",
    ]
    deflectable: Literal["yes", "no"] = Field(
        description="yes ONLY if the KB fully answers it with no account lookup, data change, approval or staff action."
    )
    confidence_score: float = Field(
        ge=0.0, le=1.0,
        description="Probability that all four fields are correct. Use below 0.8 for vague, multi-issue or borderline tickets.",
    )
    english_query: str = Field(
        description="The customer's actual request restated in one English sentence, keeping error codes and product terms."
    )


class CriticVerdict(BaseModel):
    grounded: bool = Field(description="Every factual claim in the draft is supported by the KB excerpts.")
    safe: bool = Field(description="No promised staff actions, no requests for secrets, nothing outside policy.")
    issues: list[str] = Field(description="Short, specific problems to fix. Empty if none.")
