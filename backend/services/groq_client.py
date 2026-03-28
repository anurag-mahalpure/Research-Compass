from groq import AsyncGroq
import os
from dotenv import load_dotenv

load_dotenv()

client = AsyncGroq(api_key=os.environ.get("GROQ_API_KEY", "dummy_key"))

async def groq_structured_call(prompt: str, model: str, max_tokens: int = 1000) -> str:
    response = await client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        temperature=0.1  # Low temp for structured outputs
    )
    return response.choices[0].message.content

async def groq_streaming_call(prompt: str, model: str):
    stream = await client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2000,
        temperature=0.3,
        stream=True
    )
    async for chunk in stream:
        token = chunk.choices[0].delta.content
        if token:
            yield token
