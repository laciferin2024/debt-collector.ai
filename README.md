### Debt Collector AI

## Project Overview

The Debt Collector AI project is designed to automate the process of debt collection using AI-driven voice agents. This project leverages LiveKit to integrate large language models, text-to-speech, and speech-to-text services, enabling the AI to conduct natural and effective conversations with debtors.

## Setup Instructions

1. **Clone the Repository**
   ```bash
   git clone https://github.com/laciferin2024/debt-collector.ai
   ```
2. **Navigate to the Project Directory**
   ```bash
   cd debt-collector.ai
   ```
3. **Install Dependencies**
   Ensure you have Python 3.12 installed. Then run:
   ```bash
   uv pip install .
   ```
4. **Environment Configuration**
   Set up your environment variables in a `.env` file. Refer to `config.py` for required variables like `TWILIO_ACCOUNT_SID`, `DEEPGRAM_API_KEY`, etc.

## Key Components

- **main.py**: Contains the entry point for the application and manages the overall workflow.
- **workflows/debt_collection.py**: Implements the debt collection workflow, handling user interactions and call logic.
- **prompts/debt_collection**: Contains AI prompts and dialogue templates used during interactions.

## Usage Guide

To start the debt collection agent:
```bash
uv run main.py console
```

For automated testing and self-correction:
```bash
uv run main.py --test-bot
```

## Development Notes

- The project uses `livekit-plugins-openai` and `lambdaprompt` for LLM integration.
- Logging is configured in `main.py` for debugging and monitoring.

## Testing and Debugging

- Use the `--test-bot` flag to run automated tests.
- Logs are available in the console for troubleshooting.

## What's Next

- **Fix Twilio Outbound Call Issue**: Investigate and resolve the issue preventing outbound calls to UAE numbers using your Twilio number. Check for any region-specific restrictions or required configurations in Twilio's documentation.

- **Migrate to DeepSeek API**: Transition from OpenAI's free tier to the DeepSeek API for Challenge 2. This will help overcome the limitations of OpenAI's free tier. Update your codebase to integrate DeepSeek API calls where necessary.

- **Command-Line Options**: The application can be run with the following command-line options:
  - `--test-bot`: Runs the automated LLM testing and self-correction loop.
  - `--script <script>`: Specifies the initial bot script for testing. Defaults to a predefined script if not provided.

## Contribution Guidelines

Feel free to fork the repository and submit pull requests. For major changes, please open an issue first to discuss what you would like to change.
