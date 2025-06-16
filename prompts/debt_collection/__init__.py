"""Prompts for the debt collection workflow."""

from .prompts import (
    PAYMENT_OPTIONS,
    ai_system_message,
    ai_verify_customer_identity,
    ai_parse_payment_discussion,
    ai_resolution_confirmation,
    ai_compliance_warning,
    ai_transfer_to_agent,
    ai_technical_issue_disclaimer,
)

# Export all the necessary functions and variables
__all__ = [
    "PAYMENT_OPTIONS",
    "ai_system_message",
    "ai_verify_customer_identity",
    "ai_parse_payment_discussion",
    "ai_resolution_confirmation",
    "ai_compliance_warning",
    "ai_transfer_to_agent",
    "ai_technical_issue_disclaimer",
]
