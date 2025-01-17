import os
from openai import OpenAI

# Initialize the new OpenAI client
# (we assume OPENAI_API_KEY is set in your environment)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)


def get_chat_completion(system_prompt: str, user_prompt: str, model="gpt-4o", temperature=0.7, max_tokens=1500):
    """
    Sends a chat completion request to OpenAI using the new style:
      from openai import OpenAI
      client = OpenAI()

    Returns the text of the response.
    """
    completion = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=temperature,
        max_tokens=max_tokens
    )
    # Return the content of the first choice
    return completion.choices[0].message.content  