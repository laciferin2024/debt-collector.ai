import json
import logging
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict

# Import prompts
from prompts.debt_collection import (
    ai_verify_customer_identity,
    ai_parse_payment_discussion,
    ai_resolution_confirmation,
    ai_compliance_warning,
    ai_transfer_to_agent,
    ai_technical_issue_disclaimer,
)

from livekit import agents, rtc
from livekit.agents import Agent, AgentSession, RoomInputOptions
from livekit.api import LiveKitAPI

# SIPService is accessed through livekit_api.sip
from livekit.plugins import noise_cancellation


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
        await session.say(ai_compliance_warning())

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
        await session.say(await ai_technical_issue_disclaimer())
        raise


async def _verify_identity(session: AgentSession) -> Dict:
    """Identity verification step"""
    context = {"verified": False}
    await session.say("For security purposes, could you please verify your identity?")

    # In a real implementation, you would collect and verify identity information
    # For this example, we'll simulate a successful verification
    identity = ai_verify_customer_identity("")

    if identity:
        await session.say("Thank you for verifying your identity.")
        context["verified"] = True
    else:
        await session.say("I'm sorry, I couldn't verify your identity.")

    return context


async def _discuss_payment(session: AgentSession, context: Dict):
    """Payment discussion logic"""
    payment_options = ai_parse_payment_discussion()
    await session.say(payment_options)


async def _handle_resolution(session: AgentSession, context: Dict):
    """Final resolution handling"""
    response = ai_resolution_confirmation(
        ""
    )  # Pass empty string as we don't have details yet
    await session.say(response)
    await _save_transcript(session)


async def _save_transcript(session: AgentSession):
    """Save conversation transcript"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        transcript_path = Path(TRANSCRIPTS_DIR) / f"transcript_{timestamp}.json"

        transcript = {
            "participants": [
                p.identity for p in session.ctx.room.participants.values()
            ],
            "history": [msg.to_dict() for msg in session.history.messages],
            "metadata": session.ctx.room.metadata,
        }

        with open(transcript_path, "w") as f:
            json.dump(transcript, f, indent=2)

    except Exception as e:
        logger.error(f"Transcript save failed: {e}")


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

        # Start agent session with the debt collection agent
        agent = Agent(
            instructions="You are a professional debt collection agent for Riverline Bank. "
            "Your goal is to help customers resolve their outstanding balances "
            "while maintaining a professional and empathetic tone.",
        )

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
