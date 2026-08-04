# Package init for agentaudit: exposes public API for the AgentAudit library.

from dotenv import load_dotenv

# Loads OPENAI_API_KEY / GEMINI_API_KEY (and anything else) from a .env file
# in the current working directory, if present. Real environment variables
# already set always take precedence over .env values.
load_dotenv()
