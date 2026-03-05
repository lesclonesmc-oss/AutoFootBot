import discord
import asyncio
import re
import os
from datetime import datetime, timezone
from flask import Flask
from threading import Thread

TOKEN = os.environ.get("TOKEN")
print(f"Token lu : '{TOKEN}'")

FOOTBALL_NATION_WEBHOOK_ID = "1476014023593164840"  # Webhook → Match ended
FOOTBALL_NATION_ID = "809853895450427403"           # Vrai bot → prochains matchs

CHANNEL_IDS = [
    1475202086172889140,
    1475241380451188869,
    1475205369788629143,
    1475206701127827498,
    1476013967854928043,
    1475246253393838160,
]

# ── Flask pour UptimeRobot ──
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot en ligne !"

Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080))), daemon=True).start()

# ── Bot ──
scheduled_tasks = {}

class MyClient(discord.Client):
    async def on_ready(self):
        print(f"Connecté en tant que {self.user}")

    async def on_message(self, message):
        if message.channel.id not in CHANNEL_IDS:
            return

        if not message.embeds:
            return

        # ── Webhook → détecte "Match ended" → envoie /live-upcoming ──
        if str(message.author.id) == FOOTBALL_NATION_WEBHOOK_ID:
            for embed in message.embeds:
                for field in embed.fields:
                    if "Match ended" in field.name:
                        print(f"[{message.channel.name}] Match ended détecté !")
                        await message.channel.send("/live-upcoming")
                        print(f"[{message.channel.name}] /live-upcoming envoyé")
                        return

        # ── Football Nation → lit les prochains matchs → planifie /predict ──
        if str(message.author.id) == FOOTBALL_NATION_ID:
            for embed in message.embeds:
                for field in embed.fields:
                    matches = re.findall(
                        r'[\w\s]+:\s*\[([^\]]+)\]\([^\)]+\) start time: <t:(\d+):[^>]+>',
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
                        await self._send_predict(message.channel, match_formatted)
                    else:
                        print(f"[{message.channel.name}] /predict dans {delay/60:.1f} min")

                        if message.channel.id in scheduled_tasks:
                            old_task = scheduled_tasks[message.channel.id]
                            if not old_task.done():
                                old_task.cancel()

                        scheduled_tasks[message.channel.id] = asyncio.create_task(
                            self._schedule_predict(message.channel, match_formatted, delay)
                        )
                    return

    async def _schedule_predict(self, channel, match_name: str, delay: float):
        try:
            await asyncio.sleep(delay)
            await self._send_predict(channel, match_name)
        except asyncio.CancelledError:
            print(f"[{channel.name}] Tâche annulée")

    async def _send_predict(self, channel, match_name: str):
        await channel.send(f"/predict match:{match_name}")
        print(f"[{channel.name}] /predict match:{match_name} envoyé")

client = MyClient()
client.run(TOKEN)

