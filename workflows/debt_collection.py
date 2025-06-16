"""Debt collection workflow implementation."""

import logging
from datetime import datetime
from typing import Dict, Any

from livekit.agents import AgentSession

# Import prompts
from prompts.debt_collection.prompts import (
    ai_parse_payment_discussion,
    ai_resolution_confirmation,
    ai_compliance_warning,
    ai_technical_issue_disclaimer,
)

logger = logging.getLogger(__name__)


class DebtCollectionWorkflow:
    """Handles the complete debt collection workflow."""

    def __init__(self, session: AgentSession):
        """Initialize with an active agent session."""
        self.session = session
        self.context: Dict[str, Any] = {
            "verified": False,
            "customer_info": {},
            "call_start_time": datetime.utcnow().isoformat(),
        }

    async def run(self) -> None:
        """Execute the complete debt collection workflow."""
        try:
            if not await self._check_compliance():
                await self.session.say(
                    "This call cannot proceed due to regional regulations."
                )
                return

            await self._start_conversation()

            if not await self._verify_identity():
                return

            await self._discuss_payment()
            await self._handle_resolution()

        except Exception as e:
            logger.error(f"Workflow error: {e}", exc_info=True)
            await self.session.say(ai_technical_issue_disclaimer)
            raise

    async def _start_conversation(self) -> None:
        """Start the conversation with compliance warnings and introduction."""
        await self.session.say(ai_compliance_warning)
        await self.session.say(
            "Hello, this is an automated call from Riverline Bank regarding your outstanding balance."
        )

    async def _verify_identity(self) -> bool:
        """Verify the caller's identity using account information."""
        while True:
            await self.session.say(
                "For security purposes, could you please provide the last 4 digits of your account number?"
            )

            try:
                response = await self.session.listen()
                account_last4 = response.strip()

                if not (account_last4.isdigit() and len(account_last4) == 4):
                    await self.session.say(
                        "Please provide exactly 4 digits for your account number."
                    )
                    continue

                if account_last4 != "1234":
                    await self.session.say(
                        "The account number you provided doesn't match our records. Please try again."
                    )
                    continue

                # Identity verified successfully
                self.context.update(
                    {
                        "verified": True,
                        "customer_info": {
                            "account": f"XXXX{account_last4}",
                            "amount": "$1,234.56",
                            "due_date": "2025-06-30",
                        },
                        "account_last4": account_last4,
                    }
                )

                await self.session.say(
                    f"Thank you for verifying your identity. I see you have an outstanding balance of {self.context['customer_info']['amount']} on account ending in {account_last4}."
                )
                return True

            except Exception as e:
                logger.error(f"Error during identity verification: {e}")
                await self.session.say(
                    "I encountered an error while verifying your identity. Let's try again."
                )
                return False

    async def _check_compliance(self) -> bool:
        """Check if the call complies with regional regulations."""
        # In a real implementation, this would check the caller's region
        # against compliance rules
        return True

    async def _discuss_payment(self) -> bool:
        """Discuss payment options with the caller."""
        if not self.context.get("verified"):
            await self.session.say(
                "I'll need to verify your identity before discussing payment options."
            )
            return False

        try:
            payment_options = ai_parse_payment_discussion()
            await self.session.say(payment_options)
            return True

        except Exception as e:
            logger.error(f"Error discussing payment: {e}")
            return False

    async def _handle_resolution(self) -> None:
        """Handle the resolution of the call."""
        try:
            resolution = ai_resolution_confirmation()
            await self.session.say(resolution)

        except Exception as e:
            logger.error(f"Error handling resolution: {e}")
            raise
