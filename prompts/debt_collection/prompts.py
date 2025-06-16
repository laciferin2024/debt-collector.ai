"""Prompts for the debt collection workflow using simple functions."""

# Payment options
PAYMENT_OPTIONS = {
    "full": "Pay in full today",
    "installment": "Set up an installment plan",
    "deferment": "Discuss payment deferment options",
}


def ai_system_message():
    """Return the system message for the debt collection agent."""
    return """You are an empathetic debt collection agent for Riverline Bank. 
- Maintain professionalism while showing understanding of the customer's situation.
- Use active listening and rephrase customer concerns to show understanding.
- Offer clear payment options and explain next steps.
- Escalate to a human agent if the customer becomes upset or requests it."""


def ai_verify_customer_identity(response):
    """Verify customer identity with placeholder data."""
    return {"account": "1234", "dob": "01/01/1980", "amount": "$100"}


def ai_parse_payment_discussion(concern=None):
    """Generate payment discussion prompt."""
    options = "\n".join(f"- {k}: {v}" for k, v in PAYMENT_OPTIONS.items())
    prompt = f"""You are a debt collection agent discussing payment options with a customer.
Present the payment options professionally and handle their response with empathy.

Available payment options:
{options}

If they're unable to pay, discuss alternative arrangements.
Be clear but understanding about the consequences of non-payment."""
    if concern:
        prompt += f"\n\nCustomer's concern: {concern}"
    return prompt


def ai_resolution_confirmation(details):
    """Generate resolution confirmation text."""
    return f"""Summarize the agreed-upon resolution and next steps for the customer.
    
Include:
- The payment arrangement details
- When the next payment is due (if applicable)
- Any reference numbers or confirmation details
- How they can contact support if they have questions

Resolution details: {details}"""


# Compliance warning
ai_compliance_warning = "This call is being recorded for quality and compliance purposes. By continuing this conversation, you consent to the recording."

# Transfer to agent
ai_transfer_to_agent = "I understand you'd like to speak with a representative. Please hold while I transfer you to an available agent who can assist you further."

# Technical issue
ai_technical_issue_disclaimer = "We're experiencing technical difficulties. Please call us back at [support number] or try again later."
