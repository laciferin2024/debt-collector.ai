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
from livekit.api import LiveKitAPI

# SIPService is accessed through livekit_api.sip
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
                noise_cancellation=noise_cancellation.BVC(), text_enabled=True
            ),
        )

        # Store the context in the session for use in the workflow
        session.ctx = ctx

        # Start the debt collection workflow in the background
        workflow = DebtCollectionWorkflow(session)

        asyncio.create_task(workflow.run())

    except Exception as e:
        logger.error(f"Entrypoint error: {e}")
        raise

    await ctx.connect()


if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))
