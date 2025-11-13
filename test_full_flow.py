#!/usr/bin/env python3
"""
End-to-end test of the morning brief assistant with MCP server.
This will actually fetch data, generate a summary, create a voice note, and send to Slack.
"""

import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set up logging to see what's happening
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)
logger = logging.getLogger("test")

def check_env_vars():
    """Check if required environment variables are set."""
    required = ["MCP_SERVER_URL"]
    optional_but_important = [
        "SLACK_BOT_TOKEN",
        "SLACK_USER_ID",
        "NOTION_API_KEY",
        "NOTION_TASK_DATABASE_ID",
        "GOOGLE_TOKEN_BASE64",
        "OPENAI_API_KEY",
        "ELEVENLABS_API_KEY",
    ]
    
    missing_required = []
    for var in required:
        if not os.getenv(var):
            missing_required.append(var)
    
    if missing_required:
        logger.error(f"Missing required environment variables: {', '.join(missing_required)}")
        return False
    
    missing_optional = []
    for var in optional_but_important:
        if not os.getenv(var):
            missing_optional.append(var)
    
    if missing_optional:
        logger.warning(f"Missing optional environment variables (some features may not work): {', '.join(missing_optional)}")
    
    return True

def test_mcp_connection():
    """Test if we can connect to the MCP server."""
    from src.mcp_client import MCPClient
    
    server_url = os.getenv("MCP_SERVER_URL")
    if not server_url:
        logger.error("MCP_SERVER_URL not set")
        return False
    
    logger.info(f"Testing connection to MCP server: {server_url}")
    
    try:
        client = MCPClient(server_url, timeout=10)
        # Try to call a tool that doesn't require auth to test connection
        # We'll just test the connection by checking if server responds
        logger.info("✓ MCP client initialized successfully")
        client.close()
        return True
    except Exception as e:
        logger.error(f"✗ Failed to connect to MCP server: {e}")
        return False

def run_full_test():
    """Run the actual morning brief script."""
    logger.info("=" * 60)
    logger.info("Starting full end-to-end test")
    logger.info("=" * 60)
    
    # Check environment
    if not check_env_vars():
        logger.error("Environment check failed. Please set required variables.")
        return 1
    
    # Test MCP connection
    if not test_mcp_connection():
        logger.error("MCP connection test failed.")
        return 1
    
    logger.info("")
    logger.info("Running main morning brief script...")
    logger.info("This will:")
    logger.info("  1. Fetch calendar events from Google Calendar")
    logger.info("  2. Fetch emails from Gmail")
    logger.info("  3. Fetch tasks from Notion")
    logger.info("  4. Generate a summary")
    logger.info("  5. Generate a voice script with OpenAI")
    logger.info("  6. Synthesize speech with ElevenLabs")
    logger.info("  7. Send text summary and audio file to Slack")
    logger.info("")
    
    # Import and run main
    try:
        from src.main import main
        result = main()
        
        if result == 0:
            logger.info("")
            logger.info("=" * 60)
            logger.info("✓ SUCCESS! Check your Slack for the morning brief!")
            logger.info("=" * 60)
            return 0
        else:
            logger.error("")
            logger.error("=" * 60)
            logger.error("✗ Script completed with errors (check logs above)")
            logger.error("=" * 60)
            return result
    except Exception as e:
        logger.error(f"✗ Error running main script: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(run_full_test())

