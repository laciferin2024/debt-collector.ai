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

from config import *



# Initialize Twilio client
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

class DebtCollectionAgent(Agent):
    def __init__(self):
        super().__init__(
            instructions="""You are a professional debt collection agent. 
            Be polite but firm. Follow this workflow:
            1. Verify customer identity
            2. Explain purpose of call
            3. Offer payment options
            4. Handle objections
            5. Confirm resolution or follow-up"""
        )

async def make_call(phone_number: str):
    call = twilio_client.calls.create(
        url=TWILIO_URL,
        to=phone_number,
        from_=TWILIO_NUMBER,
        record=True
    )
    return call.sid

async def debt_collection_workflow(session: AgentSession):
    try:
        # Step 1: Initial greeting
        await session.say("Hello, may I speak to [Customer Name] please?")
        
        # Step 2: Verify identity
        response = await session.generate_reply(
            instructions="Ask for last 4 digits of account number"
        )
        # ... validation logic ...

        # Step 3: State purpose
        await session.say("This call is regarding your overdue payment of $500.")
        
        # Step 4: Payment options
        options = {
            "full_payment": "Pay full amount today",
            "installment": "Setup payment plan",
            "dispute": "Dispute the charge"
        }
        choice = await session.generate_reply(
            instructions=f"Offer these options: {options}",
            tools=[function_tool]
        )
        
        # Step 5: Handle response
        if choice == "full_payment":
            await process_payment(session)
        elif choice == "installment":
            await setup_installment(session)
        elif choice == "dispute":
            await handle_dispute(session)

    except Exception as e:
        await session.say("Apologies, we're experiencing technical difficulties.")
        raise e

async def entrypoint(ctx: agents.JobContext):
    session = AgentSession(
        stt=deepgram.STT(model="nova-3"),
        llm=openai.LLM(model="gpt-4o-mini"),
        tts=cartesia.TTS(model="sonic-2"),
        vad=silero.VAD.load(),
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVCTelephony()
        )
    )
    
    # Start recording
    egress_req = api.RoomCompositeEgressRequest(
        room_name=ctx.room.name,
        audio_only=True,
        file_outputs=[api.EncodedFileOutput(
            file_type=api.EncodedFileType.MP3,
            filepath="debt_collection_recording.mp3"
        )]
    )
    
    await session.start(
        room=ctx.room,
        agent=DebtCollectionAgent(),
        workflow=debt_collection_workflow
    )
    
    # Save transcript on shutdown
    async def save_transcript():
        with open("transcript.json", "w") as f:
            f.write(session.history.to_json())
    
    ctx.add_shutdown_callback(save_transcript)
    await ctx.connect()

if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))
