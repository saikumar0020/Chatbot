import os
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
load_dotenv()
from utils.config_loader import load_config

def load_llm(provider: str = 'groq'):
    llm = None
    config = load_config()
    if provider == 'groq': 
        print("Loading LLM from Groq..............")
        groq_api_key = os.getenv("GROQ_API_KEY")
        model_name = config['llm'][provider]['model_name']
        llm=ChatGroq(model=model_name, api_key=groq_api_key)
        print("Successfully loaded model --> ", model_name)
    
    if provider == 'openai': 
        print("Loading LLM from OpenAI..............")
        openai_api_key = os.getenv("OPENAI_API_KEY")
        model_name = config['llm'][provider]['model_name']
        llm = ChatOpenAI(model=model_name, api_key=openai_api_key)
        print("Successfully loaded model --> ", model_name)
    return llm
