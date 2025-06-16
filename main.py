import json
import logging
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

# Import prompts
from prompts.debt_collection.prompts import (
    ai_parse_payment_discussion,
    ai_resolution_confirmation,
    ai_compliance_warning,
    ai_technical_issue_disclaimer,
)

from livekit import agents, rtc
from livekit.agents import Agent, AgentSession, RoomInputOptions
from livekit.plugins import noise_cancellation

from workflows.debt_collection import DebtCollectionWorkflow

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
    TWILIO_ACCOUNT_SID,
    TWILIO_AUTH_TOKEN,
    TWILIO_NUMBER,
    TWILIO_WEBHOOK_URL,
    RECORDINGS_DIR,
    TRANSCRIPTS_DIR,
)


# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def list_sip_trunks():
    """List all available SIP trunks."""
    logger.warning("SIP trunk listing is not available in this implementation")
    return []


async def make_outbound_call(phone_number: str, room_name: str) -> None:
    """Initiate an outbound call to phone_number and connect to the specified LiveKit room via SIP."""
    import asyncio
    from livekit import api
    from livekit.protocol.sip import CreateSIPParticipantRequest
    from config import (
        SIP_TRUNK_ID,
        SIP_KRISP_ENABLED,
        SIP_DEFAULT_PARTICIPANT_IDENTITY,
        SIP_DEFAULT_PARTICIPANT_NAME,
        SIP_CALL_TIMEOUT
    )
    
    logger.info(f"Initiating LiveKit SIP outbound call to {phone_number} for room {room_name}...")
    livekit_api = api.LiveKitAPI()
    request = CreateSIPParticipantRequest(
        sip_trunk_id=SIP_TRUNK_ID,
        sip_call_to=phone_number,
        room_name=room_name,
        participant_identity=SIP_DEFAULT_PARTICIPANT_IDENTITY,
        participant_name=SIP_DEFAULT_PARTICIPANT_NAME,
        krisp_enabled=SIP_KRISP_ENABLED,
        wait_until_answered=True
    )
    try:
        participant = await livekit_api.sip.create_sip_participant(request)
        logger.info(f"Successfully created SIP participant: {participant}")
        return participant
    except Exception as e:
        logger.error(f"Error creating SIP participant: {e}", exc_info=True)
        raise
    finally:
        await livekit_api.aclose()



async def entrypoint(ctx: agents.JobContext):
    """LiveKit agent entrypoint"""
    try:
        # Initialize AI components with minimal configuration
        session = AgentSession()

        # Log that we're starting the agent
        logger.info("Starting debt collection agent")

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
                noise_cancellation=noise_cancellation.BVC(), text_enabled=True
            ),
        )

        # Store the context in the session for use in the workflow
        session.ctx = ctx

        # Make outbound call to the customer using the same room as the agent session
        phone_number = "+971504301247"  # The phone number to call

        logger.info(f"Initiating outbound call to {phone_number}...")
        try:
            await make_outbound_call(phone_number, ctx.room.name)
        except Exception as e:
            logger.error(f"Call failed: {e}")
            # Optionally, you might want to clean up or retry here
            raise

        # Start the debt collection workflow in the background
        workflow = DebtCollectionWorkflow(session)
        asyncio.create_task(workflow.run())

    except Exception as e:
        logger.error(f"Entrypoint error: {e}")
        raise

    await ctx.connect()


if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))
