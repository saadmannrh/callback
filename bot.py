import json
import os

import discord
from discord.ext import tasks, commands
import asyncio

TOKEN = os.getenv('DISCORD_TOKEN')
DATA_FILE = 'tasks.json'

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)


def load_data():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'w') as f:
            json.dump({}, f)
        return
    with open(DATA_FILE, 'r') as f:
        try:
            return json.load(f)
        except json.decoder.JSONDecodeError:
            return {}

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f)

active_tasks = load_data()

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    if not nag_loop.is_running():
        nag_loop.start()


@bot.command()
async def new_task(ctx, member: discord.Member, *, task: str):

    thread = await ctx.message.create_thread(
        name=f"Project: {task}",
        auto_archive_duration=10080
    )

    active_tasks[thread.id] = {
        "user_id": member.id,
        "task": task,
        "nag_count": 0,
        "is_nagging": True
    }

    save_data(active_tasks)


    welcome_msg = (
        f"🎯 **New Task:**  {task}\n"
        f"👤 **Assignee:**  {member.mention}\n\n"
        "I will nag you every 6 hours. To stop me, type **'task complete'** in this thread."
    )
    await thread.send(welcome_msg)
    await ctx.send(f"Tracking initiated in {thread.mention}")


@bot.event
async def on_message(message):
    # Ignore bot's own messages
    if message.author == bot.user:
        return

    channel_id_str = str(message.channel.id)

    if channel_id_str in active_tasks:
        content = message.content.lower()
        if "task complete" in content:
            active_tasks[channel_id_str]["is_nagging"] = False
            save_data(active_tasks)

            task_data = active_tasks[channel_id_str]
            nags = task_data['nag_count']

            summary = (
                f"✅ **Mission Accomplished!**\n"
                f"The task '{task_data['task']}' is finished.\n"
                f"It only took {nags} nags to get you moving. Well done."
            )
            await message.channel.send(summary)
            return

    await bot.process_commands(message)


@tasks.loop(hours=6)
async def nag_loop():
    for thread_id_str, data in list(active_tasks.items()):
        # Only nag if the boolean field is True
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
    """Show all currently active projects."""
    if not active_tasks:
        await ctx.send("No active projects. Everyone is slacking.")
        return

    report = "**Current Project Status:**\n"
    for tid, data in active_tasks.items():
        report += f"• {data['project']} (Assignee: <@{data['user_id']}>) - Nagged {data['nag_count']} times.\n"
    await ctx.send(report)


bot.run(TOKEN)