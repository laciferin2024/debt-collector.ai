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
    """Handles debt collection operations including call management and customer interactions.
    
    Attributes:
        livekit_api: Client for LiveKit API interactions
        sip_service: Service for SIP call functionality
        recordings_dir: Directory to store call recordings
        transcripts_dir: Directory to store conversation transcripts
    """
    
    def __init__(self):
        """Initialize the DebtCollectionAgent with required services and directories."""
        self.recordings_dir = Path(RECORDINGS_DIR)
        self.transcripts_dir = Path(TRANSCRIPTS_DIR)
        self._setup_directories()
        self._initialize_services()
    
    def _setup_directories(self) -> None:
        """Create required directories if they don't exist."""
        try:
            self.recordings_dir.mkdir(parents=True, exist_ok=True)
            self.transcripts_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Directories set up: {self.recordings_dir}, {self.transcripts_dir}")
        except OSError as e:
            logger.error(f"Failed to create directories: {e}")
            raise
    
    def _initialize_services(self) -> None:
        """Initialize external service connections."""
        try:
            self.livekit_api = LiveKitAPI(
                url=LIVEKIT_URL, 
                api_key=LIVEKIT_API_KEY, 
                api_secret=LIVEKIT_API_SECRET
            )
            self.sip_service = self.livekit_api.sip
            logger.info("Successfully initialized LiveKit API and SIP service")
        except Exception as e:
            logger.error(f"Failed to initialize services: {e}")
            raise
    
    async def make_call(self, to_number: str) -> Optional[str]:
        """Initiate an outbound call using LiveKit SIP.
        
        Args:
            to_number: The phone number to call (in E.164 format)
            
        Returns:
            str: Call ID if successful, None otherwise
        """
        try:
            response = await self.sip_service.create_sip_call(
                to_number=to_number,
                from_number=TWILIO_NUMBER,
                sip_trunk_id="your-sip-trunk-id",
                room_name=f"sip-call-{datetime.now().timestamp()}",
                participant_identity=f"caller-{datetime.now().timestamp()}",
                participant_name="Caller",
            )
            logger.info(f"Successfully initiated SIP call to {to_number}")
            return response.call_id
            
        except Exception as e:
            logger.error(f"Failed to initiate SIP call to {to_number}: {e}")
            return None
    
    async def transfer_to_human(self, session: AgentSession, reason: str) -> None:
        """Transfer the call to a human agent.
        
        Args:
            session: The current agent session
            reason: Reason for transfer (for logging and analytics)
        """
        try:
            logger.info(f"Initiating transfer to human agent. Reason: {reason}")
            await session.say("Let me transfer you to a representative.")
            await session.room.update_metadata({"transfer_reason": reason})
            await session.disconnect()
            logger.info("Successfully transferred call to human agent")
        except Exception as e:
            logger.error(f"Failed to transfer to human agent: {e}")
            raise


    async def start_call_workflow(self, session: AgentSession) -> None:
        """Start the debt collection call workflow.
        
        Args:
            session: The agent session for the call
        """
        try:
            if not await self._check_compliance(session.ctx.room):
                await session.say("This call cannot proceed due to regional regulations.")
                return

            await self._play_compliance_warning(session)
            await self._start_conversation(session)
            
        except Exception as e:
            logger.error(f"Error in call workflow: {e}")
            await session.say(ai_technical_issue_disclaimer)
            raise
    
    async def _play_compliance_warning(self, session: AgentSession) -> None:
        """Play compliance warning and introduction."""
        await session.say(ai_compliance_warning)
        await session.say(
            "Hello, this is an automated call from Riverline Bank regarding your outstanding balance."
        )
    
    async def _start_conversation(self, session: AgentSession) -> None:
        """Handle the main conversation flow."""
        context = await self._verify_identity(session)
        if not context.get("verified"):
            return
            
        await self._discuss_payment(session, context)
        await self._handle_resolution(session, context)
    
    async def _verify_identity(self, session: AgentSession) -> Dict[str, Any]:
        """Verify the caller's identity.
        
        Returns:
            Dict containing verification status and customer info
        """
        context = {"verified": False, "customer_info": {}}
        
        try:
            await session.say(
                "For security purposes, could you please provide the last 4 digits of your account number?"
            )
            
            response = await session.listen()
            account_last4 = response.strip()
            
            if not await self._validate_account_number(account_last4, session):
                return context
                
            identity = {
                "account": f"XXXX{account_last4}",
                "amount": "$1,234.56",
                "due_date": (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d"),
            }
            
            context.update({
                "verified": True,
                "customer_info": identity,
                "account_last4": account_last4,
            })
            
            await session.say(
                f"Thank you for verifying your identity. I see you have an outstanding "
                f"balance of {identity['amount']} on account ending in {account_last4}."
            )
            
        except Exception as e:
            logger.error(f"Identity verification failed: {e}")
            await session.say("I encountered an error while verifying your identity. Let's try again.")
            
        return context
    
    async def _validate_account_number(self, account_last4: str, session: AgentSession) -> bool:
        """Validate the provided account number."""
        if not (account_last4.isdigit() and len(account_last4) == 4):
            await session.say("Please provide exactly 4 digits for your account number.")
            return False
            
        # In a real implementation, verify against your database
        if account_last4 != "1234":  # Example validation
            await session.say(
                "The account number you provided doesn't match our records. Please try again."
            )
            return False
            
        return True
    
    async def _discuss_payment(self, session: AgentSession, context: Dict[str, Any]) -> bool:
        """Discuss and process payment options with the customer."""
        if not context.get("verified"):
            await session.say("I'll need to verify your identity before discussing payment options.")
            return False
            
        try:
            payment_options = ai_parse_payment_discussion()
            await session.say(payment_options)
            
            # Simulate payment processing
            await asyncio.sleep(2.0)
            await session.say("I'll help you set up a payment plan for your outstanding balance.")
            await asyncio.sleep(1.0)
            
            customer_info = context.get("customer_info", {})
            await session.say(
                f"I've set up a 3-month payment plan for your balance of {customer_info.get('amount', 'the amount')}. "
                f"The first payment will be due on {customer_info.get('due_date', 'the due date')}."
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Payment discussion failed: {e}")
            await session.say("I encountered an error while processing your request. Let's try again.")
            return False
    
    async def _handle_resolution(self, session: AgentSession, context: Dict[str, Any]) -> None:
        """Handle the final resolution of the call."""
        try:
            resolution_details = {
                "status": "completed",
                "customer_verified": context.get("verified", False),
                "account": context.get("customer_info", {}).get("account", "unknown"),
                "timestamp": datetime.now().isoformat(),
                "resolution": "payment_plan_created",
                "payment_plan": {
                    "duration_months": 3,
                    "amount": context.get("customer_info", {}).get("amount", "unknown"),
                    "first_payment_due": context.get("customer_info", {}).get("due_date", "unknown"),
                },
            }
            
            response = ai_resolution_confirmation(str(resolution_details))
            await session.say(response)
            await asyncio.sleep(1.5)
            
            await self._save_transcript(session)
            await session.say("Thank you for calling Riverline Bank. Have a great day!")
            
        except Exception as e:
            logger.error(f"Resolution handling failed: {e}")
            await session.say("I encountered an error while finalizing your request.")
            await self._save_transcript(session)
            raise
    
    async def _save_transcript(self, session: AgentSession) -> None:
        """Save the conversation transcript."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            transcript_path = self.transcripts_dir / f"transcript_{timestamp}.json"
            
            if not hasattr(session, "history"):
                logger.warning("Session has no history attribute")
                return
                
            transcript_data = session.history.to_dict()
            
            with open(transcript_path, "w") as f:
                json.dump(transcript_data, f, indent=2)
                
            logger.info(f"Transcript saved to {transcript_path}")
            
        except Exception as e:
            logger.error(f"Failed to save transcript: {e}", exc_info=True)
    
    async def _check_compliance(self, room: rtc.Room) -> bool:
        """Check if the call complies with regional regulations."""
        # In a real implementation, check room metadata or participant location
        return True


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
        agent = DebtCollectionAgent()
        asyncio.create_task(agent.start_call_workflow(session))

    except Exception as e:
        logger.error(f"Entrypoint error: {e}")
        raise

    await ctx.connect()


if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))
