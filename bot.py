import json
import os
import time

import discord
from discord.ext import tasks, commands
import asyncio
from groq_handler import ask_llm

TOKEN = os.getenv('DISCORD_TOKEN')

DATA_DIR = 'data'
DATA_FILE = os.path.join(DATA_DIR,'tasks.json')


if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)


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
        "error", "not working", "callback", "can"
    ]

    text = text.lower()

    if "?" in text:
        return True

    for t in triggers:
        if t in text:
            return True

    return False


async def answer_question(ctx, question, details):
    await ctx.typing()

    try:
        answer = await ask_llm(question=question, task_details=details)
    except Exception as e:
        print(e)
        return

    await send_message_in_chunks(ctx, answer)

async def send_message_in_chunks(ctx, msg):
    chunks = [msg[i:i + 1900] for i in range(0, len(msg), 1900)]

    for chunk in chunks:
        await ctx.send(chunk)

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

    try:
        thread = await ctx.message.create_thread(
            name= task_title,
            auto_archive_duration=10080
        )
    except Exception as e:
        print(f"Something went wrong while creating thread: {e}")
        return

    task_started_at = time.time() * 1000
    last_nagged_at = task_started_at

    active_tasks[str(thread.id)] = {
        "user_id": member.id,
        "task": task_title,
        "details": task_details,
        "nag_count": 0,
        "is_nagging": True,
        "task_started_at": task_started_at,
        "last_nagged_at":last_nagged_at
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


@bot.event
async def on_message(message):

    if message.author == bot.user:
        return

    channel_id_str = str(message.channel.id)
    content = message.content.lower()

    if looks_like_question(content):
       await answer_question(ctx=message.channel, question=content, details=None)

    if channel_id_str in active_tasks:

        if "task complete" in content:

            active_tasks[channel_id_str]["is_nagging"] = False
            save_data(active_tasks)

            task_data = active_tasks[channel_id_str]

            summary = (
                f"✅ **Mission Accomplished!**\n"
                f"The task '{task_data['task']}' is finished.\n"
                f"It only took {task_data['nag_count']} nags. \n"
            )

            await message.channel.send(summary)

            await asyncio.sleep(60)

            if isinstance(message.channel, discord.Thread):
                await message.channel.delete()
            return

        if looks_like_question(content):

            task_data = active_tasks[channel_id_str]
            task_details = task_data["details"]

            await answer_question(message.channel, content, task_details)

    await bot.process_commands(message)


@tasks.loop(minutes=1)
async def nag_loop():
    for thread_id_str, data in list(active_tasks.items()):
        if not data.get("is_nagging", False):
            continue

        thresh_hold = 1000 * 60 * 60 * 6 # 6 hours
        last_nagged_at = data.get("last_nagged_at")
        now_ms = int(time.time() * 1000)

        print(f"Checking task {data['task']}: Last nagged {(now_ms - last_nagged_at)//(1000*60)} min ago ")

        if last_nagged_at is None:
            last_nagged_at = 0
            data['last_nagged_at'] = 0
            save_data(active_tasks)

        if now_ms - last_nagged_at < thresh_hold:
            continue

        thread = bot.get_channel(int(thread_id_str))

        if not thread:
            try:
                thread = await bot.fetch_channel(int(thread_id_str))
            except discord.NotFound:
                del active_tasks[thread_id_str]
                save_data(active_tasks)
                continue

        if thread:
            data['nag_count'] += 1
            data['last_nagged_at'] = now_ms
            save_data(active_tasks)

            user_mention = f"<@{data['user_id']}>"
            await thread.send(
                f"⏰ **NAG #{data['nag_count']}**\n"
                f"Hey {user_mention}, where's the update on **{data['task']}**? \n"
                "I will nag you every 6 hours. To stop me, type **'task complete'** in this thread. \n"
                "If you need any help just ask me in this thread."
            )


@bot.command()
async def status(ctx):
    nagging_tasks = {tid: data for tid, data in active_tasks.items() if data.get("is_nagging")}

    if not nagging_tasks:
        await ctx.send("No active tasks. Everyone is slacking.")
        return

    report = "**Current Task Status:**\n"
    for tid, data in nagging_tasks.items():
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

    try:
       await answer_question(ctx=ctx, question=title, details=details)
    except Exception as e:
        print(e)
        await thinking.edit(content="Callback failed to respond.")
        return

bot.run(TOKEN)