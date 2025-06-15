import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from livekit import agents, api
from livekit.agents import AgentSession, Agent, RoomInputOptions
from livekit.plugins import (
    deepgram, 
    cartesia,
    openai,
    noise_cancellation,
    silero
)
from twilio.rest import Client
import os
import asyncio
import json

from config import *

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Twilio client
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

class DebtCollectionAgent(Agent):
    def __init__(self):
        super().__init__(
            instructions="""
            You are a professional debt collection agent for Riverline Bank. 
            Your goal is to collect overdue credit card payments while maintaining 
            a professional and empathetic tone. Follow this workflow:
            
            1. Verify customer identity
            2. Explain purpose of call
            3. Offer payment options
            4. Handle objections
            5. Confirm resolution or follow-up
            
            Key points:
            - Always verify customer identity first
            - Be empathetic but firm
            - Offer flexible payment options
            - Document all interactions
            - Follow compliance guidelines
            """
        )

async def make_call(phone_number: str, call_reason: str = "overdue_payment") -> Optional[str]:
    """
    Make an outbound call using Twilio.
    
    Args:
        phone_number: The phone number to call
        call_reason: The reason for the call (default: "overdue_payment")
        
    Returns:
        The call SID if successful, None otherwise
    """
    try:
        call = twilio_client.calls.create(
            url=TWILIO_URL,
            to=phone_number,
            from_=TWILIO_NUMBER,
            record=True,
            status_callback=f"{TWILIO_URL}/status",
            status_callback_method="POST"
        )
        logger.info(f"Call initiated to {phone_number}, SID: {call.sid}")
        return call.sid
    except Exception as e:
        logger.error(f"Failed to make call: {str(e)}")
        return None

async def debt_collection_workflow(session: AgentSession):
    """
    Main workflow for debt collection conversation.
    """
    try:
        # Initialize conversation context
        context = {
            "customer_verified": False,
            "payment_options": {
                "full_payment": "Pay full amount today",
                "installment": "Setup payment plan",
                "deferment": "Request payment deferment"
            }
        }

        # Step 1: Initial greeting and verification
        await session.say("Hello, this is Riverline Bank. May I speak to [Customer Name] please?")
        
        # Wait for response and verify identity
        response = await session.generate_reply(
            instructions="""
            Verify customer identity by asking for:
            1. Last 4 digits of account number
            2. Date of birth
            3. Last payment amount
            
            If verification fails, end call professionally.
            """
        )
        
        if not response:
            await session.say("I'm sorry, I couldn't verify your identity. Goodbye.")
            return

        # Step 2: Explain purpose
        await session.say("""
        I'm calling regarding your overdue credit card payment of $500. 
        This amount is now 30 days past due. Would you like to discuss payment options?
        """)

        # Step 3: Present payment options
        response = await session.generate_reply(
            instructions="""
            Offer these payment options:
            1. Pay full amount today
            2. Set up installment plan
            3. Request payment deferment
            
            Handle customer objections professionally.
            """
        )

        # Step 4: Handle customer response
        if "full_payment" in response.lower():
            await process_payment(session)
        elif "installment" in response.lower():
            await setup_installment(session)
        elif "deferment" in response.lower():
            await handle_deferment(session)
        else:
            await handle_objection(session)

    except Exception as e:
        logger.error(f"Workflow error: {str(e)}")
        await session.say("I apologize, but we're experiencing technical difficulties. Please call back later.")
        raise e

async def process_payment(session: AgentSession):
    """
    Handle full payment processing.
    """
    await session.say("""
    Great! We can process your payment through:
    1. Credit card
    2. Bank transfer
    3. Online payment portal
    
    Which method would you prefer?
    """)
    # Add payment processing logic here

async def setup_installment(session: AgentSession):
    """
    Handle installment plan setup.
    """
    await session.say("""
    I can help you set up an installment plan. 
    How many monthly payments would you prefer?
    """)
    # Add installment plan logic here

async def handle_deferment(session: AgentSession):
    """
    Handle payment deferment requests.
    """
    await session.say("""
    I understand your situation. Let's discuss a payment deferment.
    Could you explain why you're having difficulty making the payment?
    """)
    # Add deferment logic here

async def handle_objection(session: AgentSession):
    """
    Handle customer objections.
    """
    await session.say("""
    I understand your concerns. Let's find a solution that works for you.
    Would you like to:
    1. Discuss alternative payment options
    2. Set up a payment plan
    3. Talk to a supervisor
    """)
    # Add objection handling logic here

async def entrypoint(ctx: agents.JobContext):
    """
    Main entrypoint for LiveKit agent.
    """
    try:
        # Create session with enhanced plugins
        session = AgentSession(
            stt=deepgram.STT(model="nova-3"),
            llm=openai.LLM(model="gpt-4o-mini"),
            tts=cartesia.TTS(model="sonic-2", voice="en-US-Standard-D"),
            vad=silero.VAD.load(),
            room_input_options=RoomInputOptions(
                noise_cancellation=noise_cancellation.BVCTelephony(),
                echo_cancellation=True,
                automatic_gain_control=True
            )
        )

        # Set up recording
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        recording_path = Path("recordings") / f"debt_collection_{timestamp}.mp3"
        recording_path.parent.mkdir(exist_ok=True)

        egress_req = api.RoomCompositeEgressRequest(
            room_name=ctx.room.name,
            audio_only=True,
            file_outputs=[api.EncodedFileOutput(
                file_type=api.EncodedFileType.MP3,
                filepath=str(recording_path)
            )]
        )

        # Start agent
        await session.start(
            room=ctx.room,
            agent=DebtCollectionAgent(),
            workflow=debt_collection_workflow
        )

        # Save transcript on shutdown
        async def save_transcript():
            try:
                transcript_path = Path("transcripts") / f"debt_collection_{timestamp}.json"
                transcript_path.parent.mkdir(exist_ok=True)
                
                with open(transcript_path, "w") as f:
                    json.dump({
                        "timestamp": timestamp,
                        "conversation": session.history.to_json(),
                        "metadata": {
                            "customer_verified": True,
                            "resolution_status": "pending"
                        }
                    }, f, indent=2)
                
                logger.info(f"Transcript saved to {transcript_path}")
            except Exception as e:
                logger.error(f"Failed to save transcript: {str(e)}")

        ctx.add_shutdown_callback(save_transcript)
        
        await ctx.connect()

    except Exception as e:
        logger.error(f"Agent initialization failed: {str(e)}")
        raise e

if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))
