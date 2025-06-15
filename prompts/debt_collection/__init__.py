"""Prompts for the debt collection workflow using lambdaprompt."""
from lambdaprompt import Prompt
from typing import Dict, Any

# System message for the LLM
system_prompt = Prompt(
    """You are an empathetic debt collection agent for Riverline Bank. 
- Maintain professionalism while showing understanding of the customer's situation.
- Use active listening and rephrase customer concerns to show understanding.
- Offer clear payment options and explain next steps.
- Escalate to a human agent if the customer becomes upset or requests it."""
)

# Identity verification prompt
verify_identity = Prompt(
    """Extract the following information from the customer's response:
    - Last 4 digits of account (as "account")
    - Date of birth in MM/DD/YYYY format (as "dob")
    - Last payment amount (as "amount")
    
    If any information is missing, ask follow-up questions to collect it.
    
    Customer response: {{response}}""",
    output_parser=dict
)

# Payment options
PAYMENT_OPTIONS = {
    "full": "Pay in full today",
    "installment": "Set up an installment plan",
    "deferment": "Discuss payment deferment options"
}

# Payment discussion prompt
payment_discussion = Prompt(
    """You are a debt collection agent discussing payment options with a customer.
    Present the payment options professionally and handle their response with empathy.
    
    Available payment options:
    {% for key, value in options.items() %}
    - {{ key }}: {{ value }}
    {% endfor %}
    
    If they're unable to pay, discuss alternative arrangements.
    Be clear but understanding about the consequences of non-payment.
    
    Customer's concern: {{concern | default(None)}}"""
)

# Resolution confirmation prompt
resolution_confirmation = Prompt(
    """Summarize the agreed-upon resolution and next steps for the customer.
    
    Include:
    - The payment arrangement details
    - When the next payment is due (if applicable)
    - Any reference numbers or confirmation details
    - How they can contact support if they have questions
    
    Resolution details: {{details}}"""
)

# Compliance warning prompt
compliance_warning = Prompt(
    "This call is being recorded for quality and compliance purposes. "
    "By continuing this conversation, you consent to the recording."
)

# Transfer to agent prompt
transfer_to_agent = Prompt(
    "I understand you'd like to speak with a representative. "
    "Please hold while I transfer you to an available agent who can assist you further."
)

# Technical issue prompt
technical_issue = Prompt(
    "We're experiencing technical difficulties. "
    "Please call us back at [support number] or try again later."
)

# Helper function to get system message
def get_system_message() -> str:
    return str(system_prompt)

# Helper function to verify identity
async def verify_customer_identity(response: str) -> Dict[str, Any]:
    return await verify_identity(response=response)

# Helper function for payment discussion
async def discuss_payment(concern: str = None) -> str:
    return await payment_discussion(options=PAYMENT_OPTIONS, concern=concern)

# Helper function for resolution confirmation
async def confirm_resolution(details: str) -> str:
    return await resolution_confirmation(details=details)
