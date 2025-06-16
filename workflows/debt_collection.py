"""Debt collection workflow implementation."""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from livekit.agents import (
    AgentSession,
    UserInputTranscribedEvent,
    ConversationItemAddedEvent,
)
import asyncio

from livekit.api import ChatMessage

# Import prompts
from prompts.debt_collection.prompts import (
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

        self.session.on("user_input_transcribed", self.on_user_input)  # TODO:
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

            await asyncio.sleep(3)

            # user_input = await self.session.generate_reply(
            #     user_input="1234",
            #     instructions="Listen for the user's response containing 4 digits and acknowledge receipt",
            # )

            user_input = self.captured_input

            logger.info(f"Captured input: {user_input}")
            try:
                account_last4 = self.extract_digits(user_input)

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
        """Discuss payment options with the caller in a natural conversation."""
        if not self.context.get("verified"):
            await self.session.say(
                "For security reasons, I'll need to verify your identity before we discuss payment options. "
                "Could you please confirm the last 4 digits of your account number?"
            )
            return False

        try:
            # Start with empathy and understanding
            await self.session.say(
                f"I understand that managing finances can be challenging. Let's work together to find a solution "
                f"that works for you regarding your balance of {self.context['customer_info']['amount']}."
            )

            # Present payment options naturally
            await self.session.say(
                "You have a few options available:"
                "\n1. You can pay the full amount today."
                "\n2. We can set up a payment plan that fits your budget."
                "\n3. If you're experiencing financial hardship, we can discuss potential assistance programs."
                "\nWhich option would you like to explore?"
            )

            # Simulate user selecting an option (in a real scenario, this would come from user input)
            self.waiting_for_input = True
            await asyncio.sleep(2)  # Simulate user response time

            # For demo purposes, we'll assume they chose a payment plan
            # In a real implementation, this would be determined by user input
            self.context["payment_plan"] = {
                "amount": "$250",
                "start_date": (datetime.utcnow() + timedelta(days=7)).strftime(
                    "%B %d, %Y"
                ),
                "installments": 5,
                "next_payment_amount": "$50",
                "next_payment_date": (datetime.utcnow() + timedelta(days=7)).strftime(
                    "%B %d, %Y"
                ),
            }

            return True

        except Exception as e:
            logger.error(f"Error discussing payment options: {e}", exc_info=True)
            await self.session.say(
                "I apologize, but I'm having trouble accessing your account information. "
                "Let me transfer you to a representative who can assist you further."
            )
            return False

    async def handle_resolution(self) -> None:
        """Handle the resolution of the call with a natural conversation flow."""
        try:
            # Confirm the resolution with the customer
            await self.session.say("Let me confirm the details we've discussed:")

            # Summarize the agreement
            if self.context.get("payment_plan"):
                plan = self.context["payment_plan"]
                summary = (
                    f"You've agreed to a payment plan of {plan.get('amount')} "
                    f"starting on {plan.get('start_date')} with "
                    f"{plan.get('installments')} monthly payments. "
                    f"Your next payment of {plan.get('next_payment_amount')} "
                    f"is due on {plan.get('next_payment_date')}."
                )
                await self.session.say(summary)
            else:
                await self.session.say(
                    "I'll process your payment now. Please hold for a moment while I confirm the transaction."
                )
                # Simulate processing time
                await asyncio.sleep(2)
                await self.session.say(
                    "Thank you, your payment has been processed successfully."
                )

            # Provide reference information
            ref_number = f"REF-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
            await self.session.say(
                f"Your reference number is {ref_number}. "
                "I'll email you a confirmation with all these details right away."
            )

            # Ask for confirmation
            await self.session.say(
                "Is there anything else I can assist you with today?"
            )

            # Wait for response (simplified for example)
            self.waiting_for_input = True
            await asyncio.sleep(2)  # Simulate user response time

            # Close the conversation
            await self.session.say(
                "Thank you for your time today. Have a wonderful day!"
            )

            # Update context with resolution details
            self.context.update(
                {
                    "resolution": "success",
                    "reference_number": ref_number,
                    "call_end_time": datetime.utcnow().isoformat(),
                }
            )

            # Log successful resolution
            logger.info(f"Successfully resolved call with reference {ref_number}")

        except Exception as e:
            logger.error(f"Error handling resolution: {e}", exc_info=True)
            await self.session.say(
                "I apologize, but I'm having trouble processing this request. "
                "Please hold while I transfer you to a representative who can assist you further."
            )
            # Set error state in context
            self.context.update(
                {
                    "resolution": "error",
                    "error": str(e),
                    "call_end_time": datetime.utcnow().isoformat(),
                }
            )

    def on_user_input(self, event: UserInputTranscribedEvent):
        logger.debug("User input received: {}".format(event.transcript))
        if self.waiting_for_input:
            self.captured_input = event.transcript
            self.waiting_for_input = False

    def on_conversation_item_added(self, event: ConversationItemAddedEvent):
        logger.debug("Conversation item added: {}".format(event))
        msg: ChatMessage = event.item

        # capture user input if we are waiting for it
        # TODO: simulate user
        if self.waiting_for_input:  # and msg.role == "user":
            self.captured_input = "1234"
            self.waiting_for_input = False
            logger.debug(f"User input set: {self.captured_input}")
