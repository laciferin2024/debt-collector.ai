import asyncio
import json
import logging
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

from livekit import agents, rtc
from livekit.agents import Agent, AgentSession, RoomInputOptions
from livekit.agents.llm import ChatContext, ChatMessage, ChatRole
from livekit.plugins import noise_cancellation
from livekit.plugins import openai as lk_openai


# --- Challenge 2: Automated Testing & Self-Correcting Voice Agent ---


async def generate_persona_llm(model=None):
    """
    Generate a synthetic loan defaulter persona using LLM.
    Returns a dict with persona details and conversation style.
    """
    system = "You are a generator of realistic loan defaulter personas. Each persona should have a name, age, financial background, reason for default, attitude (e.g. evasive, cooperative, angry, anxious), and a short backstory."
    prompt = "Generate a persona as a JSON object with keys: name, age, background, default_reason, attitude, backstory."

    llm_instance = lk_openai.LLM(model=model or "gpt-3.5-turbo")

    # Create a ChatContext with structured messages
    chat_context = ChatContext()
    chat_context.messages = [
        ChatMessage(role="system", content=[system]),
        ChatMessage(role="user", content=[prompt]),
    ]

    # Call .chat() with the keyword argument and await the stream
    stream = llm_instance.chat(chat_ctx=chat_context)

    # Collect the response content
    content = ""
    async for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            content += chunk.choices[0].delta.content

    try:
        persona = json.loads(content.strip())
    except Exception:
        persona = {
            "name": "Alex",
            "age": 38,
            "background": "Recently lost job, single parent",
            "default_reason": "Unemployment",
            "attitude": random.choice(["evasive", "cooperative", "angry", "anxious"]),
            "backstory": "Alex lost their job due to layoffs and is struggling to pay bills.",
        }
    return persona


async def simulate_conversation_llm(persona, bot_script, model=None, max_turns=8):
    """
    Simulate a conversation between the debt collection bot and a generated persona.
    Returns the full conversation as a list of dicts: [{role, text}]
    """
    llm_instance = lk_openai.LLM(model=model or "gpt-3.5-turbo")
    conversation = []
    system = f"You are a customer named {persona['name']} who is {persona['attitude']} about a debt collection call. Your backstory: {persona['backstory']}. Respond realistically."
    user_msg = bot_script

    for turn in range(max_turns):
        # Bot speaks
        conversation.append({"role": "bot", "text": user_msg})

        # Persona responds
        prompt = f"Debt collector said: '{user_msg}'. How do you respond?"

        # Create a ChatContext with structured messages
        chat_context = ChatContext()
        chat_context.messages = [
            ChatMessage(role=ChatRole.SYSTEM, content=[system]),
            ChatMessage(role=ChatRole.USER, content=[prompt]),
        ]

        # Call .chat() with the keyword argument and await the stream
        stream = llm_instance.chat(chat_ctx=chat_context)

        # Collect the response content
        content = ""
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                content += chunk.choices[0].delta.content

        conversation.append({"role": "user", "text": content.strip()})
        # Optionally, bot can adapt script here (for now, keep static)
        user_msg = bot_script  # In future: adapt to persona's last response
    return conversation


def analyze_metrics(conversation):
    """
    Analyze the conversation for repetition and negotiation effectiveness.
    Returns a dict of metrics.
    """
    repetition_count = 0
    negotiation_score = 0
    bot_lines = [msg["text"] for msg in conversation if msg["role"] == "bot"]
    user_lines = [msg["text"] for msg in conversation if msg["role"] == "user"]
    # Repetition: count duplicate bot lines
    repetition_count = len(bot_lines) - len(set(bot_lines))
    # Negotiation: check for negotiation keywords in bot and user lines
    negotiation_keywords = [
        "plan",
        "arrangement",
        "options",
        "installment",
        "work with you",
        "negotiate",
        "alternative",
    ]
    negotiation_score = sum(
        any(kw in line.lower() for kw in negotiation_keywords) for line in bot_lines
    )
    return {
        "repetition": repetition_count,
        "negotiation_score": negotiation_score,
    }


async def rewrite_bot_script_llm(conversation, metrics, old_script, model=None):
    """
    Use LLM to rewrite the bot's script based on poor metrics.
    Returns a new script string.
    """
    llm_instance = lk_openai.LLM(model=model or "gpt-3.5-turbo")
    system = "You are a voice agent script improver. Given a conversation and its weaknesses, rewrite the debt collector's script to reduce repetition and improve negotiation."
    prompt = (
        f"Conversation:\n{json.dumps(conversation, indent=2)}\n"
        f"Metrics: {metrics}\n"
        f"Old Script: {old_script}\n"
        "Rewrite the bot script to address the weaknesses. Return only the new script."
    )

    # Create a ChatContext with structured messages
    chat_context = ChatContext()
    chat_context.messages = [
        ChatMessage(role=ChatRole.SYSTEM, content=[system]),
        ChatMessage(role=ChatRole.USER, content=[prompt]),
    ]

    # Call .chat() with the keyword argument and await the stream
    stream = llm_instance.chat(chat_ctx=chat_context)

    # Collect the response content
    content = ""
    async for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            content += chunk.choices[0].delta.content

    return content.strip()


async def self_correcting_test_loop(
    bot_script, max_iters=3, repetition_threshold=1, negotiation_threshold=2, model=None
):
    """
    Main loop: generate personas, simulate conversations, analyze, self-correct until thresholds met or max_iters.
    Returns final script and metrics.
    """
    script = bot_script
    for i in range(max_iters):
        persona = await generate_persona_llm(model=model)
        conversation = await simulate_conversation_llm(persona, script, model=model)
        metrics = analyze_metrics(conversation)
        print(f"[Test {i + 1}] Persona: {persona['name']} | Metrics: {metrics}")
        if (
            metrics["repetition"] <= repetition_threshold
            and metrics["negotiation_score"] >= negotiation_threshold
        ):
            print(f"Success: Script passed thresholds after {i + 1} iteration(s).")
            return script, metrics
        script = await rewrite_bot_script_llm(
            conversation, metrics, script, model=model
        )
        print(f"[Self-correction] Script updated for next iteration.")
    print("Final script after self-correction:", script)
    return script, metrics


# --- End Challenge 2 additions ---
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
    RECORDINGS_DIR,
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
        SIP_CALL_TIMEOUT,
        SIP_DEFAULT_PARTICIPANT_IDENTITY,
        SIP_DEFAULT_PARTICIPANT_NAME,
        SIP_KRISP_ENABLED,
        SIP_TRUNK_ID,
    )

    logger.info(
        f"Initiating LiveKit SIP outbound call to {phone_number} for room {room_name}..."
    )
    livekit_api = api.LiveKitAPI()
    request = CreateSIPParticipantRequest(
        sip_trunk_id=SIP_TRUNK_ID,
        sip_call_to=phone_number,
        room_name=room_name,
        participant_identity=SIP_DEFAULT_PARTICIPANT_IDENTITY,
        participant_name=SIP_DEFAULT_PARTICIPANT_NAME,
        krisp_enabled=SIP_KRISP_ENABLED,
        wait_until_answered=True,
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
            # raise

        # Start the debt collection workflow in the background
        workflow = DebtCollectionWorkflow(session)
        asyncio.create_task(workflow.run())

    except Exception as e:
        logger.error(f"Entrypoint error: {e}")
        raise

    await ctx.connect()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Debt Collector AI Main")
    parser.add_argument(
        "--test-bot",
        action="store_true",
        help="Run automated LLM testing/self-correction loop",
    )
    parser.add_argument(
        "--script",
        type=str,
        default="Hello, this is Riverline Bank. I'm calling to discuss your outstanding balance and help you find a resolution. Can we talk about your payment options?",
        help="Initial bot script for testing",
    )
    args = parser.parse_args()
    if args.test_bot:
        # Run the automated testing + self-correcting loop (Challenge 2)
        asyncio.run(self_correcting_test_loop(args.script))
    else:
        agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))
