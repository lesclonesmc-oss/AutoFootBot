import discord
from discord.ext import tasks
import requests
from datetime import datetime, timedelta
from flask import Flask
from threading import Thread

# ---------------- CONFIG ----------------
TOKEN = "MTQ3NTIzMDA1MzQ4NjAzOTA4MQ.G-hiBQ.6XBuYaJy0mUzppW8ImmgPJB6ILYf-aTksGPWYA"
API_KEY = "13da01bc231922b485f78a93e3621f3f"

# Salons Discord
SALONS = {
    "real-madrid": 1475202086172889140,           # #real-madrid
    "ligue-1": 1475206701127827498,               # #ligue-1
    "uefa-champions-league": 1475205369788629143,# #uefa-champions-league
    "lens": 1475241380451188869,                  # #lens
    "coupe-du-monde": 1475246253393838160        # #coupe-du-monde
}

# Ligues à suivre
LEAGUES = {
    "ligue-1": 61,
    "uefa-champions-league": 2,
    "coupe-du-monde": 1   # API-Football ID Coupe du Monde (à vérifier)
}

# Clubs spécifiques
CLUBS = {
    "real-madrid": 541,  # Real Madrid ID API-Football
    "lens": 116          # Lens ID API-Football
}

# ---------------------------------------

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# -------------- Flask pour rester actif --------------
app = Flask('')

@app.route('/')
def home():
    return "Bot Discord actif!"

def run():
    app.run(host='0.0.0.0', port=8080)

Thread(target=run).start()

# ------------------------------------------------------

def get_upcoming_matches():
    matches = []

    # 1️⃣ Matchs Ligue 1, LDC, Coupe du Monde
    for league_name, league_id in LEAGUES.items():
        url = f"https://v3.football.api-sports.io/fixtures?league={league_id}&next=50"
        headers = {"x-apisports-key": API_KEY}
        res = requests.get(url, headers=headers).json()
        for f in res['response']:
            match_time = datetime.fromisoformat(f['fixture']['date'][:-1])
            matches.append({
                "home": f['teams']['home']['name'],
                "away": f['teams']['away']['name'],
                "time": match_time,
                "league": league_name
            })

    # 2️⃣ Matchs Real Madrid et Lens (tous championnats)
    for club_name, club_id in CLUBS.items():
        url_club = f"https://v3.football.api-sports.io/fixtures?team={club_id}&next=50"
        headers = {"x-apisports-key": API_KEY}
        res_club = requests.get(url_club, headers=headers).json()
        for f in res_club['response']:
            match_time = datetime.fromisoformat(f['fixture']['date'][:-1])
            matches.append({
                "home": f['teams']['home']['name'],
                "away": f['teams']['away']['name'],
                "time": match_time,
                "league": club_name
            })

    return matches

@client.event
async def on_ready():
    print("Bot prêt !")
    check_matches.start()

@tasks.loop(minutes=5)
async def check_matches():
    matches = get_upcoming_matches()
    now = datetime.utcnow()
    for m in matches:
        delta = m['time'] - now

        # 40 minutes avant le match → prédiction
        if timedelta(minutes=39) < delta <= timedelta(minutes=40):
            salon_id = SALONS[m['league']]
            channel = client.get_channel(salon_id)
            if channel:
                await channel.send(f"/predict match:{m['home']} vs {m['away']}")
                print(f"Predicted {m['home']} vs {m['away']} in {m['league']}")

        # Après le match (~2h après) → live-upcoming
        elif timedelta(minutes=-5) < delta <= timedelta(minutes=-1):
            salon_id = SALONS[m['league']]
            channel = client.get_channel(salon_id)
            if channel:
                await channel.send("/live-upcoming")
                print(f"Live updated for {m['league']}")

client.run(TOKEN)