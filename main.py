import json
import logging
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict

from livekit import agents, rtc, api
from livekit.agents import AgentSession, RoomInputOptions
from livekit.plugins import (
    deepgram,
    cartesia,
    openai,
    noise_cancellation,
    silero,
    turn_detector,
)
from livekit.plugins.turn_detector.multilingual import MultilingualModel


# Configuration
from config import (
    DEEPGRAM_API_KEY,
    OPENAI_API_KEY,
    CARTESIA_API_KEY,
    TWILIO_ACCOUNT_SID,
    TWILIO_AUTH_TOKEN,
    TWILIO_NUMBER,
    RECORDINGS_DIR,
    TRANSCRIPTS_DIR,
    COMPLIANCE_REGIONS,
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

        # Initialize Twilio SIP provider
        self.sip_provider = api.SIPProvider(
            vendor="twilio",
            auth={"account_sid": TWILIO_ACCOUNT_SID, "auth_token": TWILIO_AUTH_TOKEN},
        )

    def _create_dirs(self):
        self.recordings_dir.mkdir(parents=True, exist_ok=True)
        self.transcripts_dir.mkdir(parents=True, exist_ok=True)

    async def make_call(self, to_number: str) -> Optional[str]:
        """Initiate outbound call using LiveKit SIP"""
        try:
            sip_part = await self.sip_provider.create_participant(
                from_number=TWILIO_NUMBER, to_number=to_number
            )
            return sip_part.id
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
        # Check regional compliance
        if not await _check_compliance(session):
            await session.say("This call cannot proceed due to regional regulations.")
            return

        # Configure LLM for empathetic responses
        await session.llm.configure(
            temperature=0.3,
            system_message="""Respond with empathy while maintaining professionalism.
            Use conversational repair strategies for misunderstandings.
            Escalate when detecting high emotional stress.""",
        )

        # Conversation steps
        context = await _verify_identity(session)
        if not context.get("verified"):
            return

        await _discuss_payment(session, context)
        await _handle_resolution(session, context)

    except Exception as e:
        logger.error(f"Workflow error: {e}")
        await session.say(
            "We're experiencing technical difficulties. Please call back later."
        )
        raise


async def _verify_identity(session: AgentSession) -> Dict:
    """Identity verification step"""
    context = {"verified": False}
    await session.say(
        "Hello, this is Riverline Bank. May I speak to the account holder?"
    )

    # Collect verification info
    responses = await session.llm.extract(
        instructions="""Extract:
        - Last 4 digits of account
        - Date of birth (MM/DD/YYYY)
        - Last payment amount"""
    )

    if all(k in responses for k in ["account", "dob", "amount"]):
        context["verified"] = True
        await session.say("Thank you for verifying.")
    else:
        await session.say("Unable to verify. Goodbye.")

    return context


async def _discuss_payment(session: AgentSession, context: Dict):
    """Payment discussion logic"""
    options = {
        "full": "Pay in full today",
        "installment": "Set up installment plan",
        "deferment": "Discuss payment deferment",
    }

    response = await session.llm.generate(
        prompt=f"""Present options: {options}. 
        Handle objections professionally."""
    )

    await session.say(response)


async def _handle_resolution(session: AgentSession, context: Dict):
    """Final resolution handling"""
    response = await session.llm.generate(prompt="Confirm resolution and next steps.")

    await session.say(response)
    await _save_transcript(session)


async def _save_transcript(session: AgentSession):
    """Save conversation transcript"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        transcript_path = Path(TRANSCRIPTS_DIR) / f"transcript_{timestamp}.json"

        transcript = {
            "participants": [p.identity for p in session.room.participants.values()],
            "history": [msg.to_dict() for msg in session.history.messages],
            "metadata": session.room.metadata,
        }

        with open(transcript_path, "w") as f:
            json.dump(transcript, f, indent=2)

    except Exception as e:
        logger.error(f"Transcript save failed: {e}")


async def _check_compliance(session: AgentSession) -> bool:
    """Check regional compliance regulations"""
    location = session.room.participant.location
    return location in COMPLIANCE_REGIONS


async def entrypoint(ctx: agents.JobContext):
    """LiveKit agent entrypoint"""
    try:
        # Initialize AI components
        session = AgentSession(
            stt=deepgram.STT(model="nova-3"),
            llm=openai.LLM(model="gpt-4o-mini"),
            tts=cartesia.TTS(model="sonic-2", voice="en-US-Standard-D"),
            vad=silero.VAD.load(),
            turn_detection=MultilingualModel(),
            room_input_options=RoomInputOptions(
                noise_cancellation=noise_cancellation.BVC()
            ),
        )

        # Start call recording
        recording_path = Path(RECORDINGS_DIR) / f"call_{datetime.now().timestamp()}.m4a"
        egress = rtc.RoomEgress(
            audio_output=rtc.EncodedAudioOutput(
                file_type=rtc.EncodedFileType.M4A, filepath=str(recording_path)
            )
        )
        await ctx.room.start_egress(egress)

        # Start agent session
        await session.start(
            room=ctx.room,
            agent=DebtCollectionAgent(),
            workflow=debt_collection_workflow,
        )

    except Exception as e:
        logger.error(f"Entrypoint error: {e}")
        raise

    await ctx.connect()


if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))
