import discord
import asyncio
import re
from datetime import datetime, timezone
from flask import Flask
from threading import Thread

# ── Config ──
TOKEN = "MTQ3ODg4OTY2Njk0OTI4Nzk1MA.Gzsb9z.fIPSagnV00ri7VmC41gk6yACy_X0L4gbTeBA38"

BOT_MATCH_ENDED_ID = "809853895450427403"  # Football Nation → "Match ended" → /live-upcoming
BOT_UPCOMING_ID = "668075833780469772"     # Autre bot → prochains matchs → /predict

CHANNEL_IDS = [
    1475202086172889140,  # real-madrid
    1475241380451188869,  # lens
    1475205369788629143,  # uefa-champions-league
    1475206701127827498,  # ligue-1
    1476013967854928043,  # premier-league
    1475246253393838160,  # coupe-du-monde
]

# ── Flask (pour Render) ──
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot en ligne !"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

Thread(target=run_flask, daemon=True).start()

# ── Bot ──
client = discord.Client()
scheduled_tasks = {}

@client.event
async def on_ready():
    print(f"Connecté en tant que {client.user}")

@client.event
async def on_message(message):
    if message.channel.id not in CHANNEL_IDS:
        return

    # ── Football Nation "Match ended" → /live-upcoming ──
    if str(message.author.id) == BOT_MATCH_ENDED_ID:
        for embed in message.embeds:
            for field in embed.fields:
                if "Match ended" in field.name:
                    print(f"[{message.channel.name}] Match ended détecté !")
                    await message.channel.send("/live-upcoming")
                    print(f"[{message.channel.name}] /live-upcoming envoyé")
                    return

    # ── Autre bot → /predict 40 min avant ──
    if str(message.author.id) == BOT_UPCOMING_ID:
        if not message.embeds:
            return

        for embed in message.embeds:
            for field in embed.fields:
                matches = re.findall(
                    r'\[([^\]]+)\]\([^\)]+\) start time: <t:(\d+):[^>]+>',
                    field.value
                )
                if not matches:
                    continue

                now = datetime.now(timezone.utc).timestamp()

                future_matches = [
                    (name, int(ts))
                    for name, ts in matches
                    if int(ts) > now
                ]

                if not future_matches:
                    print(f"[{message.channel.name}] Aucun match à venir")
                    continue

                future_matches.sort(key=lambda x: x[1])
                match_name, match_ts = future_matches[0]

                match_formatted = match_name.replace(" - ", " vs ")
                delay = match_ts - now - (40 * 60)

                match_dt = datetime.fromtimestamp(match_ts, tz=timezone.utc)
                print(f"[{message.channel.name}] Prochain match : {match_formatted} à {match_dt.strftime('%d/%m %H:%M')} UTC")

                if delay <= 0:
                    print(f"[{message.channel.name}] Moins de 40 min, envoi immédiat !")
                    await send_predict(message.channel, match_formatted)
                else:
                    print(f"[{message.channel.name}] /predict dans {delay/60:.1f} min")

                    if message.channel.id in scheduled_tasks:
                        old_task = scheduled_tasks[message.channel.id]
                        if not old_task.done():
                            old_task.cancel()

                    scheduled_tasks[message.channel.id] = asyncio.create_task(
                        schedule_predict(message.channel, match_formatted, delay)
                    )
                return

async def schedule_predict(channel, match_name: str, delay: float):
    try:
        await asyncio.sleep(delay)
        await send_predict(channel, match_name)
    except asyncio.CancelledError:
        print(f"[{channel.name}] Tâche annulée")

async def send_predict(channel, match_name: str):
    await channel.send(f"/predict match:{match_name}")
    print(f"[{channel.name}] /predict match:{match_name} envoyé")

client.run(TOKEN)

