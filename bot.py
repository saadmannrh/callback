import os

import discord
from discord.ext import tasks, commands
import asyncio

TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.messages = True
bot = commands.Bot(command_prefix="!", intents=intents)

active_nags = {}

active_projects = {}


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    if not nag_loop.is_running():
        nag_loop.start()


@bot.command()
async def start_project(ctx, member: discord.Member, *, project_name: str):
    """Starts a new project thread and begins the 6-hour nag cycle."""

    # Create the thread
    thread = await ctx.message.create_thread(
        name=f"Project: {project_name}",
        auto_archive_duration=10080
    )

    active_projects[thread.id] = {
        "user_id": member.id,
        "project": project_name,
        "nag_count": 0
    }

    welcome_msg = (
        f"🎯 **Project Started:** {project_name}\n"
        f"👤 **Assignee:** {member.mention}\n\n"
        "I will nag you every 6 hours. To stop me, type **'task complete'** in this thread."
    )
    await thread.send(welcome_msg)
    await ctx.send(f"Tracking initiated in {thread.mention}")


@bot.event
async def on_message(message):
    # Ignore bot's own messages
    if message.author == bot.user:
        return

    # Check if 'task complete' is said in an active project thread
    if message.channel.id in active_projects:
        content = message.content.lower()
        if "task complete" in content:
            project_data = active_projects.pop(message.channel.id)
            nags = project_data['nag_count']

            summary = (
                f"✅ **Mission Accomplished!**\n"
                f"The project '{project_data['project']}' is finished.\n"
                f"It only took {nags} nags to get you moving. Well done."
            )
            await message.channel.send(summary)
            return  # Don't process other commands if it's a completion

    await bot.process_commands(message)


@tasks.loop(hours=6)
async def nag_loop():
    for thread_id, data in list(active_projects.items()):
        thread = bot.get_channel(thread_id)
        if thread:
            data['nag_count'] += 1
            user_mention = f"<@{data['user_id']}>"
            await thread.send(
                f"⏰ **NAG #{data['nag_count']}**\n"
                f"Hey {user_mention}, where's the update on **{data['project']}**?\n"
                "Tick tock. Type 'task complete' when you're done."
            )


@bot.command()
async def status(ctx):
    """Show all currently active projects."""
    if not active_projects:
        await ctx.send("No active projects. Everyone is slacking.")
        return

    report = "**Current Project Status:**\n"
    for tid, data in active_projects.items():
        report += f"• {data['project']} (Assignee: <@{data['user_id']}>) - Nagged {data['nag_count']} times.\n"
    await ctx.send(report)


bot.run(TOKEN)