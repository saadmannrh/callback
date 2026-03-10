import os
import aiohttp

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

async def ask_llm(task_details, question):

    url = "https://api.groq.com/openai/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    system_prompt = f"""
You are a senior programming mentor helping beginner developers.

The student is working on this task:

TASK DETAILS:
{task_details}

Rules:
- explain in depth
- give examples
- avoid unnecessary complexity
- assume the user is new to programming
"""

    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question}
        ]
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=payload) as resp:
            data = await resp.json()
            return data["choices"][0]["message"]["content"]