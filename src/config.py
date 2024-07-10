import os
from dotenv import load_dotenv
from pathlib import Path
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from src.utils.custom_chat_anthropic import CustomChatAnthropic

dotenv_path = Path('../.env')
load_dotenv(dotenv_path=dotenv_path)

CLEARONE_LEADS_API_KEY = os.getenv("CLEARONE_LEADS_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

llm = ChatOpenAI(model="gpt-3.5-turbo-0125", temperature = 0, max_tokens = 1000)
# llm = CustomChatAnthropic(model = "claude-3-haiku-20240307", temperature = 0, max_tokens = 1000, api_key = ANTHROPIC_API_KEY)