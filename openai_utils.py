import os
import time
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv() 

# Initialize the OpenAI client
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("Missing OpenAI API key. Please set the OPENAI_API_KEY environment variable.")

client = OpenAI(api_key=OPENAI_API_KEY)

def get_chat_completion(system_prompt: str, user_prompt: str, model="gpt-4o", temperature=0.7, max_tokens=1500):
    """
    Sends a chat completion request to OpenAI.
    Automatically retries on rate limit errors.
    """
    retries = 3
    for attempt in range(retries):
        try:
            completion = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )
            return completion.choices[0].message.content
        except Exception as e:
            if attempt < retries - 1 and "rate limit" in str(e).lower():
                time.sleep(2 ** attempt)  # Exponential backoff for rate limit
            else:
                raise e