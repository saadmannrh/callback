import json
import os

import shutil
import discord
from discord.ext import tasks, commands
import asyncio
from groq_handler import ask_llm

TOKEN = os.getenv('DISCORD_TOKEN')

DATA_DIR = '/app/data'
DATA_FILE = os.path.join(DATA_DIR,'tasks.json')

if not os.path.exists(DATA_FILE):
    os.makedirs(DATA_DIR)

LOCAL_FILE = 'tasks.json'

if not os.path.exists(DATA_FILE) and os.path.exists(LOCAL_FILE):
    print(f"Migration: Copying {LOCAL_FILE} to {DATA_FILE}")
    shutil.copy2(LOCAL_FILE, DATA_FILE)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)


def load_data():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'w') as f:
            json.dump({}, f)
        return {}
    with open(DATA_FILE, 'r') as f:
        try:
            return json.load(f)
        except json.decoder.JSONDecodeError:
            return {}

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

active_tasks = load_data()

def looks_like_question(text):

    triggers = [
        "what", "why", "how", "help", "explain",
        "segmentation fault", "pointer", "memory",
        "linked list", "struct", "null", "bug",
        "error", "not working"
    ]

    text = text.lower()

    if "?" in text:
        return True

    for t in triggers:
        if t in text:
            return True

    return False


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    if not nag_loop.is_running():
        nag_loop.start()


@bot.command()
async def new_task(ctx, member: discord.Member, *, task: str):
    parts = task.split('\n',1)

    task_title = parts[0].strip()
    task_details = parts[1].strip() if len(parts) > 1 else ""

    thread = await ctx.message.create_thread(
        name=f"Task: {task_title}",
        auto_archive_duration=10080
    )

    active_tasks[str(thread.id)] = {
        "user_id": member.id,
        "task": task_title,
        "details": task_details,
        "nag_count": 0,
        "is_nagging": True
    }

    save_data(active_tasks)

    welcome_msg = (
        f"🎯 **New Task:** {task_title}\n"
        f"👤 **Assignee:** {member.mention}\n\n"
        f"📋 **Details:**\n{task_details}\n\n"
        "Use **!help_me ** if you need guidance.\n"
        "I will nag you every 6 hours. To stop me, type **'task complete'** in this thread."
    )

    await thread.send(welcome_msg)
    await ctx.send(f"Tracking initiated in {thread.mention}")


@bot.event
async def on_message(message):

    if message.author == bot.user:
        return

    channel_id_str = str(message.channel.id)

    if channel_id_str in active_tasks:

        content = message.content.lower()

        if "task complete" in content:

            active_tasks[channel_id_str]["is_nagging"] = False
            save_data(active_tasks)

            task_data = active_tasks[channel_id_str]

            summary = (
                f"✅ **Mission Accomplished!**\n"
                f"The task '{task_data['task']}' is finished.\n"
                f"It only took {task_data['nag_count']} nags. \n"
                "I will nag you every 6 hours. To stop me, type **'task complete'** in this thread."
            )

            await message.channel.send(summary)

            await asyncio.sleep(60)

            if isinstance(message.channel, discord.Thread):
                await message.channel.delete()
            return

        if looks_like_question(content):

            task_data = active_tasks[channel_id_str]
            task_details = task_data["details"]

            await message.channel.typing()

            try:
                answer = await ask_llm(task_details, message.content)
            except Exception as e:
                print(e)
                return

            if len(answer) > 1900:
                answer = answer[:1900]

            await message.channel.send(answer)

    await bot.process_commands(message)


@tasks.loop(hours=6)
async def nag_loop():
    for thread_id_str, data in list(active_tasks.items()):
        if not data.get("is_nagging", False):
            continue

        thread = bot.get_channel(int(thread_id_str))
        if thread:
            data['nag_count'] += 1
            save_data(active_tasks)  # Save the updated nag count

            user_mention = f"<@{data['user_id']}>"
            await thread.send(
                f"⏰ **NAG #{data['nag_count']}**\n"
                f"Hey {user_mention}, where's the update on **{data['task']}**?"
            )


@bot.command()
async def status(ctx):
    if not active_tasks:
        await ctx.send("No active tasks. Everyone is slacking.")
        return

    report = "**Current Task Status:**\n"
    for tid, data in active_tasks.items():
        report += f"• {data['task']} (Assignee: <@{data['user_id']}>) - Nagged {data['nag_count']} times.\n"
    await ctx.send(report)

@bot.command()
async def help_me(ctx):

    channel_id = str(ctx.channel.id)

    if channel_id not in active_tasks:
        await ctx.send("This command only works inside a project thread.")
        return

    task_data = active_tasks[channel_id]
    title = task_data["task"]
    details = task_data["details"]

    thinking = await ctx.send("🤖 Reviewing the task...")

    prompt = f"""
        Explain the following programming task to a beginner and suggest how they should start implementing it.
        
        TASK TITLE:
        {title}
        
        TASK DETAILS:
        {details}
        
        Explain:
        1. What the task means
        2. Key concepts needed
        3. How they should approach implementing it
        """

    try:
        answer = await ask_llm("", prompt)
    except Exception as e:
        print(e)
        await thinking.edit(content="AI failed to respond.")
        return

    chunks = [answer[i:i+1900] for i in range(0, len(answer), 1900)]


    await thinking.edit(content=chunks[0])

    for chunk in chunks[1:]:
        await ctx.send(chunk)

bot.run(TOKEN)