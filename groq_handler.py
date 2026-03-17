import os
import aiohttp

GROQ_API_KEY = os.getenv("GROQ_API_KEY")


async def ask_llm(question, task_details):
    task_details_str = "" if task_details is None or task_details == "" else f"task_details:{task_details}"
    system_prompt = f"""
    You are a discord bot named callback. Your developer is Saadman Shoumik.    
    You will work as the programming mentor helping beginner and intermediate developers.

    Your subordinate is working on this task:

    {task_details_str}

    Rules:
    - explain in depth
    - explain the low level concepts
    - c is the default language
    - give examples
    - avoid unnecessary complexity
    """

    reply = await prompt_llm(system_prompt, question)
    return reply

async def prompt_llm(system_prompt, question):

    url = "https://api.groq.com/openai/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

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