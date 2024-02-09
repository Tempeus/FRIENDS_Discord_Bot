import discord
import os
from discord.ext import commands
from dotenv import load_dotenv
import DiscordDB

# environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
OPENAI_KEY = os.getenv('OPENAI_KEY')

intents = discord.Intents.default()
intents.messages = True

bot = commands.Bot(command_prefix='!', intents=intents)
db = DiscordDB.DiscordDatabase()


@bot.event
async def on_ready():
    db.create_tables()

@bot.command(name='check_points')
async def check_points(ctx):
    # Check and display user points
    user_id = str(ctx.author.id)
    points = user_points.get(user_id, 0)
    await ctx.send(f"{ctx.author.mention}, you have {points} points.")

@bot.command(name='leaderboard')
async def leaderboard(ctx):
    # Display the top 10 players on the leaderboard
    sorted_users = sorted(user_points.items(), key=lambda x: x[1], reverse=True)[:10]

    leaderboard_message = "Leaderboard:\n"
    for idx, (user_id, points) in enumerate(sorted_users, start=1):
        member = ctx.guild.get_member(int(user_id))
        username = member.name if member else f"User not found ({user_id})"
        leaderboard_message += f"{idx}. {username}: {points} points\n"

    await ctx.send(leaderboard_message)

@bot.command(name='list_challenges')
async def list_challenges(ctx):
    # Display a list of challenges
    # You can retrieve challenges from a file, database, or hardcode them here
    challenges = ["Challenge 1: ...", "Challenge 2: ..."]
    await ctx.send("\n".join(challenges))

@bot.command(name='approve_proof')
async def approve_proof(ctx, user_mention, challenge_name, points):
    # Handle proof approval
    # Adjust user points in the database or file
    user_id = int(user_mention.strip('<@!>'))
    # Grant points to the user
    await ctx.send(f"Proof for {challenge_name} approved. {points} points awarded to <@{user_id}>.")

bot.run(TOKEN)