"""Debt collection workflow implementation."""

import logging
from datetime import datetime
from typing import Dict, Any

from livekit.agents import (
    AgentSession,
    UserInputTranscribedEvent,
    ConversationItemAddedEvent,
)
import asyncio

from livekit.api import ChatMessage

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
        self.waiting_for_input = False
        self.captured_input = None
        self.context: Dict[str, Any] = {
            "verified": False,
            "customer_info": {},
            "call_start_time": datetime.utcnow().isoformat(),
        }

        self.session.on("user_input_transcribed", self.on_user_input)
        self.session.on(
            "user_speech_transcribed", self.on_user_input
        )  # FIXME: doesn't work its for custom emit -->p

        self.session.on("conversation_item_added", self.on_conversation_item_added)

    async def run(self) -> None:
        """Execute the complete debt collection workflow."""
        try:
            if not await self.check_compliance():
                await self.session.say(
                    "This call cannot proceed due to regional regulations."
                )
                return

            await self.start_conversation()

            if not await self.verify_identity():
                return

            await self.discuss_payment()
            await self.handle_resolution()

        except Exception as e:
            logger.error(f"Workflow error: {e}", exc_info=True)
            await self.session.say(ai_technical_issue_disclaimer)
            raise

    async def start_conversation(self) -> None:
        """Start the conversation with compliance warnings and introduction."""
        await self.session.say(ai_compliance_warning)
        await self.session.say(
            "Hello, this is an automated call from Riverline Bank regarding your outstanding balance."
        )

    @staticmethod
    def extract_digits(text):
        import re

        digits = re.findall(r"\d", text)
        return "".join(digits)[-4:] if len(digits) >= 4 else "".join(digits)

    async def verify_identity(self) -> bool:
        """Verify the caller's identity using account information."""
        while True:  # todo: configure tries
            self.waiting_for_input = True
            await self.session.say(
                "For security purposes, could you please provide the last 4 digits of your account number?",
                allow_interruptions=True,
            )

            while self.waiting_for_input:
                logger.debug("waiting for input")
                await asyncio.sleep(1)

            logger.info(f"Captured input: {self.captured_input}")
            try:
                account_last4 = self.extract_digits(self.captured_input)

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

    async def check_compliance(self) -> bool:
        """Check if the call complies with regional regulations."""
        # In a real implementation, this would check the caller's region
        # against compliance rules
        return True

    async def discuss_payment(self) -> bool:
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

    async def handle_resolution(self) -> None:
        """Handle the resolution of the call."""
        try:
            resolution = ai_resolution_confirmation()
            await self.session.say(resolution)

        except Exception as e:
            logger.error(f"Error handling resolution: {e}")
            raise

    def on_user_input(self, event: UserInputTranscribedEvent):
        logger.debug("User input received: {}".format(event.transcript))
        if self.waiting_for_input:
            self.captured_input = event.transcript
            self.waiting_for_input = False

    def on_conversation_item_added(self, event: ConversationItemAddedEvent):
        logger.debug("Conversation item added: {}".format(event))
        msg: ChatMessage = event.item

        # capture user input if we are waiting for it
        if self.waiting_for_input and msg.role == "user":
            self.captured_input = msg.message
            self.waiting_for_input = False
            logger.debug(f"User input set: {self.captured_input}")
