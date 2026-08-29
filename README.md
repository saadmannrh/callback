# Callback Bot 🤖

> A Discord bot that nags your friends to finish their tasks and helps them code.

I built Callback because my friends kept making promises to finish project tasks and then completely disappearing. I needed a way to constantly remind them of their tasks. This bot relentlessly nags anyone assigned to a task every 6 hours until they get it done. But it's not just annoying, it also acts as an AI coding mentor to help them fix bugs so they have absolutely zero excuses!

---

## ⚡ What It Does

* **🎯 Clean Threads:** Automatically makes a new Discord thread for every task so the main chat doesn't get messy.
* **⏰ The Nag Loop:** Pings the assigned person every 6 hours until they finally finish the job.
* **🧠 AI Coding Mentor:** Uses Groq (`llama-3.1-8b`) to help explain low-level programming concepts.
* **🔍 Auto-Detects Cries for Help:** If someone types words like `bug`, `pointer`, or `segmentation fault` in a thread, the bot automatically jumps in with AI help.
* **💾 Doesn't Forget:** Saves all tasks to a local file. If the bot restarts, it remembers exactly who to keep nagging.

---

## 🛠️ Built With

* **Python** & `discord.py`
* `aiohttp` for fast web requests
* **Groq API** for the AI brains
