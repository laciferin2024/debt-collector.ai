import json
import logging
import os
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict

# Import prompts
from prompts.debt_collection.prompts import (
    ai_parse_payment_discussion,
    ai_resolution_confirmation,
    ai_compliance_warning,
    ai_technical_issue_disclaimer,
)

from livekit import agents, rtc
from livekit.agents import Agent, AgentSession, RoomInputOptions
from livekit.api import LiveKitAPI

# SIPService is accessed through livekit_api.sip
from livekit.plugins import noise_cancellation

# TTS using Cartesia
try:
    from livekit.plugins import cartesia

    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False
    print(
        "Warning: Cartesia TTS plugin not available. Speech synthesis will be disabled."
    )


# Configuration
from config import (
    TWILIO_NUMBER,
    RECORDINGS_DIR,
    TRANSCRIPTS_DIR,
    LIVEKIT_URL,
    LIVEKIT_API_KEY,
    LIVEKIT_API_SECRET,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DebtCollectionAgent:
    def __init__(self):
        self.recordings_dir = Path(RECORDINGS_DIR)
        self.transcripts_dir = Path(TRANSCRIPTS_DIR)
        self._create_dirs()

        # Initialize LiveKit API client
        self.livekit_api = LiveKitAPI(
            url=LIVEKIT_URL, api_key=LIVEKIT_API_KEY, api_secret=LIVEKIT_API_SECRET
        )

        # Initialize SIP service
        self.sip_service = self.livekit_api.sip

    def _create_dirs(self):
        self.recordings_dir.mkdir(parents=True, exist_ok=True)
        self.transcripts_dir.mkdir(parents=True, exist_ok=True)

    async def make_call(self, to_number: str) -> Optional[str]:
        """Initiate outbound call using LiveKit SIP"""
        try:
            # Create a SIP call using the SIP service
            # Note: You'll need to set up SIP dispatch rules in your LiveKit server first
            # This is a simplified example - you may need to adjust based on your setup
            response = await self.sip_service.create_sip_call(
                to_number=to_number,
                from_number=TWILIO_NUMBER,
                # You'll need to configure these values based on your SIP setup
                sip_trunk_id="your-sip-trunk-id",
                room_name=f"sip-call-{datetime.now().timestamp()}",
                participant_identity=f"caller-{datetime.now().timestamp()}",
                participant_name="Caller",
            )
            logger.info(f"SIP call initiated: {response}")
            return response.call_id
        except Exception as e:
            logger.error(f"SIP call failed: {e}")
            return None

    async def transfer_to_human(self, session: AgentSession, reason: str):
        """Transfer call to human agent"""
        await session.say("Let me transfer you to a representative.")
        await session.room.update_metadata({"transfer_reason": reason})
        await session.disconnect()


async def debt_collection_workflow(session: AgentSession):
    """Conversation workflow with compliance checks"""
    try:
        # Get the room from the session's context
        room = session.ctx.room

        # Check regional compliance
        if not await _check_compliance(room):
            await session.say("This call cannot proceed due to regional regulations.")
            return

        # Play compliance warning
        await session.say(ai_compliance_warning)

        # Start the conversation
        await session.say(
            "Hello, this is an automated call from Riverline Bank regarding your outstanding balance."
        )

        # Conversation steps
        context = await _verify_identity(session)
        if not context.get("verified"):
            return

        await _discuss_payment(session, context)
        await _handle_resolution(session, context)

    except Exception as e:
        logger.error(f"Workflow error: {e}")
        await session.say(ai_technical_issue_disclaimer)
        raise


async def _verify_identity(session: AgentSession) -> Dict:
    """Identity verification step"""
    context = {"verified": False, "customer_info": {}}

    # Ask for account number
    await session.say(
        "For security purposes, could you please provide the last 4 digits of your account number?"
    )

    try:
        # Get user input for the last 4 digits of their account number
        response = await session.listen()
        account_last4 = response.strip()

        # Validate the input is 4 digits
        if not (account_last4.isdigit() and len(account_last4) == 4):
            await session.say(
                "Please provide exactly 4 digits for your account number."
            )
            return await _verify_identity(session)

        # Check if the last 4 digits match the expected value
        if account_last4 != "1234":
            await session.say(
                "The account number you provided doesn't match our records. Please try again."
            )
            return await _verify_identity(session)

        identity = {
            "account": f"XXXX{account_last4}",
            "amount": "$1,234.56",
            "due_date": "2025-06-30",
        }

        context.update(
            {
                "verified": True,
                "customer_info": identity,
                "account_last4": account_last4,
            }
        )

        await session.say(
            f"Thank you for verifying your identity. I see you have an outstanding balance of {identity['amount']} on account ending in {account_last4}."
        )

    except Exception as e:
        logger.error(f"Error during identity verification: {e}")
        await session.say(
            "I encountered an error while verifying your identity. Let's try again."
        )

    return context


async def _discuss_payment(session: AgentSession, context: Dict):
    """Payment discussion logic"""
    if not context.get("verified"):
        await session.say(
            "I'll need to verify your identity before discussing payment options."
        )
        return False

    try:
        # Present payment options
        payment_options = ai_parse_payment_discussion()
        await session.say(payment_options)

        # In a real implementation, we would process user input here
        # For now, we'll simulate a payment plan selection
        await asyncio.sleep(2.0)

        # Simulate selecting a payment plan
        await session.say(
            "I'll help you set up a payment plan for your outstanding balance."
        )
        await asyncio.sleep(1.0)

        # Confirm the payment plan
        await session.say(
            f"I've set up a 3-month payment plan for your balance of {context.get('customer_info', {}).get('amount', 'the amount')}. The first payment will be due on {context.get('customer_info', {}).get('due_date', 'the due date')}."
        )

        return True

    except Exception as e:
        logger.error(f"Error during payment discussion: {e}")
        await session.say(
            "I encountered an error while processing your request. Let's try again."
        )
        return False


async def _handle_resolution(session: AgentSession, context: Dict):
    """Final resolution handling"""
    try:
        # Get resolution details based on the conversation
        resolution_details = {
            "status": "completed",
            "customer_verified": context.get("verified", False),
            "account": context.get("customer_info", {}).get("account", "unknown"),
            "timestamp": datetime.now().isoformat(),
            "resolution": "payment_plan_created",
            "payment_plan": {
                "duration_months": 3,
                "amount": context.get("customer_info", {}).get("amount", "unknown"),
                "first_payment_due": context.get("customer_info", {}).get(
                    "due_date", "unknown"
                ),
            },
        }

        # Generate confirmation message
        response = ai_resolution_confirmation(str(resolution_details))
        await session.say(response)

        # Short delay before ending the call
        await asyncio.sleep(1.5)

        # Save the transcript before ending the call
        await _save_transcript(session)

        # End the conversation
        await session.say("Thank you for calling Riverline Bank. Have a great day!")

    except Exception as e:
        logger.error(f"Error during resolution: {e}")
        await session.say("I encountered an error while finalizing your request.")
        await _save_transcript(session)
        raise


async def _save_transcript(session: AgentSession):
    """Save conversation transcript using LiveKit's built-in functionality"""
    try:
        # Ensure transcripts directory exists
        os.makedirs("transcripts", exist_ok=True)

        # Generate timestamp for filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        transcript_path = f"transcripts/transcript_{timestamp}.json"

        # Get the conversation history from the session
        if not hasattr(session, "history"):
            logger.warning("Session has no history attribute")
            return

        # Convert history to a serializable format
        transcript_data = session.history.to_dict()

        # Save to file
        with open(transcript_path, "w") as f:
            json.dump(transcript_data, f, indent=2)

        logger.info(f"Transcript saved to {transcript_path}")

    except Exception as e:
        logger.error(f"Failed to save transcript: {e}", exc_info=True)
        # Don't raise the exception to prevent workflow failure due to transcript saving issues
        logger.debug("Transcript error details:", exc_info=True)


async def _check_compliance(room: rtc.Room) -> bool:
    """Check regional compliance regulations"""
    # For now, we'll assume compliance is always true
    # In a real implementation, you would check the room's metadata or participant's location
    return True

    # Example implementation if you have location data:
    # location = room.participant.location  # This assumes the participant has a location attribute
    # return location in COMPLIANCE_REGIONS


async def entrypoint(ctx: agents.JobContext):
    """LiveKit agent entrypoint"""
    try:
        # Initialize AI components with minimal configuration
        # Note: In a production environment, you would want to properly configure these plugins
        session = AgentSession()

        # Log that we're starting the agent
        logging.info("Starting debt collection agent")

        # Prepare for call recording (if supported)
        recording_path = None
        if hasattr(rtc, "RoomEgress"):
            try:
                recording_path = (
                    Path(RECORDINGS_DIR) / f"call_{datetime.now().timestamp()}.m4a"
                )
                recording_path.parent.mkdir(parents=True, exist_ok=True)

                # Create egress for recording
                egress = rtc.RoomEgress(
                    rtc.EncodedFileOutput(
                        file_path=str(recording_path), file_type=rtc.EncodedFileType.MP4
                    )
                )
                await ctx.room.start_egress(egress)
                logger.info(f"Recording started: {recording_path}")
            except Exception as e:
                logger.warning(f"Could not start recording: {e}")
                logger.info("Continuing without recording")
                recording_path = None
        else:
            logger.info("Recording not supported in this version of LiveKit")

        # Configure agent with optional TTS
        agent_config = {
            "instructions": "You are a professional debt collection agent for Riverline Bank. "
            "Your goal is to help customers resolve their outstanding balances "
            "while maintaining a professional and empathetic tone."
        }

        # Configure Cartesia TTS if available
        if TTS_AVAILABLE:
            tts_plugin = cartesia.TTS(model="sonic-english")
            agent_config["tts"] = tts_plugin

        # Start agent session with the debt collection agent
        agent = Agent(**agent_config)

        # Start the session with the agent
        await session.start(
            room=ctx.room,
            agent=agent,
            room_input_options=RoomInputOptions(
                noise_cancellation=noise_cancellation.BVC(),
            ),
        )

        # Store the context in the session for use in the workflow
        session.ctx = ctx

        # Start the debt collection workflow in the background
        asyncio.create_task(debt_collection_workflow(session))

    except Exception as e:
        logger.error(f"Entrypoint error: {e}")
        raise

    await ctx.connect()


if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))
