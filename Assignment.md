# Assignment

## Riverline Hiring Assignment - Full Stack AI Engineer

### General Guidelines

- Keep your code short and concise.
- Feel free to use any tools that help you solve this assignment.
- The assignment has two parts. Both are compulsory.
- The assignment is designed to be hard and lengthy. Starting early will help.
- There are no right answers. Approach matters more than correctness.
- The submission form is at the end of this document.
    - This will ask for additional details, apart from your assignment.
    - Go through the form well in advance to avoid any last minute confusion.
- Reach out to us if you have any queries (jayanth@riverline.ai)
- The deadline (mentioned on the email) will be strict - no extensions! So, plan accordingly.

#### Challenge 1: Building voice agents with LiveKit

We use [LiveKit](https://livekit.io/) at Riverline to build AI voice agents. LiveKit is an open-source tool that helps connect large language models (LLMs), text-to-speech (TTS), and speech-to-text (STT) services. It also works with cloud telephony systems so that the AI can make and receive phone calls.

Your task is to build a **debt collection voice agent** using LiveKit. It should be able to call people (outbound calls) and talk to them like a real human.

You can design your own debt collection scenario (e.g., a bank reminding about overdue credit card bills, a telecom company following up on unpaid dues, etc.). Here are the requirements:

1. **Robust Voice Agent**
    - Your bot should handle edge cases (unexpected user responses, background noise, interruptions, etc.).
2. **Human-like Conversation**
    - Make the conversation feel natural and polite.
    - The voice should sound real and convincing. So, choose your models wisely.
3. **Phone Call Integration**
    - Use Twilio to dial outbound phone calls to any number. Their free credits should be able to cover and set up instructions will be available on their docs as well as LiveKit docs.
    - Tip: Use a **US number**. Indian numbers require business verification.
4. **Easy to Use**
    - Make the app simple and smooth to use.
5. **Bonus (Brownie Points)**
    - Record the call.
    - Save the transcript of the conversation using LiveKit.

Submit a code implementation of the application, along with an audio recording of you talking with the bot and a 2-3 minute Loom recording of you walking through the project. 

#### Challenge 2: Self-correcting Voice Agents

If you’ve ever built a voice agent, we would agree upon the fact that testing voice agents is harder than building one. Replicating a real-world conversations with voice agents is hard. We’re using [Cekura](https://cekura.ai) for testing our voice agents across different customer personas to identify places where our bot has to improve. Here’s a demo on how AI-automated testing of voice agents on Cekura works:  https://youtu.be/QIi6yawrWDA. A step ahead from here is, what if voice agents are able to self-correct themselves. Here’s a demo of self-correcting voice agents by [Vogent](https://vogent.ai): https://www.youtube.com/watch?v=7yKWYjlQN8U

Here’s the challenge: 

1. Build an AI-automated testing platform for voice agents. Automatically generate loan defaulter personalities, test them against deployed bot’s prompt. You can do this in chat by simulating conversation between two LLMs or even better, in voice (Brownie points for integrating the voice agent built in Challenge 1 with this application. ). Validate your testing by picking any two metrics that you would want to track for a voice agent (like, is the bot repeating itself, is the bot negotiating enough, is the bot providing irrelevant response to the customer etc.) 
2. Self-correcting voice agent: Once there is a mechanism to understand the failure points of the voice agent, the agent should be able to self-correct itself by rewriting its script, and then undergo the automated testing until a threshold is reached. Build a flow for the same.

The goal is to go from a base script for the debt collection bot, to a state where the bot handles almost every scenario possible on a real-world call, by constantly testing and iterating itself in an automated fashion. 

Submit a code implementation of the automated testing + self correcting voice agent, along with a 2-3 minute Loom recording of you walking through the project. 

#### Submission Checklist

- A GitHub repo containing (make sure that this is public and has a detailed README file):
    - Implementation of debt collection voice agent built with LiveKit
    - Self-correcting Voice Agent
- An audio recording of you talking with the voice agent
- 2-3 minute demo of LiveKit voice agent
- 2-3 minute demo of self-correcting voice agent platform
