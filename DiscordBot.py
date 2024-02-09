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
intents.members = True  # Disable typing events, if needed
intents.presences = True  # Disable presence events, if needed
intents.message_content = True    # Enable message content updates (required for commands)

bot = commands.Bot(command_prefix='!', intents=intents)
db = DiscordDB.DiscordDatabase()

@bot.event
async def on_ready():
    db.create_tables()

@bot.command(name='points')
async def check_points(ctx):
    # Check and display user points
    user_id = str(ctx.author.id)
    points = db.get_user_points(user_id)
    await ctx.send(f"{ctx.author.mention}, you have {points} points.")

@bot.command(name='leaderboard')
async def leaderboard(ctx):
    # Display the top 10 players on the leaderboard
    sorted_users = db.get_top_users()
    leaderboard_message = "Leaderboard:\n"
    for idx, (user_id, points) in enumerate(sorted_users, start=1):
        member = ctx.guild.get_member(int(user_id))
        username = member.name if member else f"User not found ({user_id})"
        leaderboard_message += f"{idx}. {username}: {points} points\n"

    await ctx.send(leaderboard_message)

@bot.command(name='create_challenge')
async def add_challenge(ctx, name, points, unique_challenge=True):
    try:
        points = int(points)
        if points < 0:
            raise ValueError("Points should be a non-negative integer.")

        # Add the challenge to the database
        db.add_challenge(name, points, unique_challenge)

        await ctx.send(f"Challenge '{name}' with {points} points added successfully.")
    except ValueError as ve:
        await ctx.send(f"Error: {ve}")
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")

@bot.command(name='list_challenges')
async def list_challenges(ctx):
    try:
        # Retrieve challenges from the database
        challenges_list = db.get_challenges()

        # Display challenges in a formatted way
        if challenges_list:
            challenge_str = "Challenges:\n"
            for challenge in challenges_list:
                challenge_str += f"ID: {challenge[0]}, Name: {challenge[1]}, Points: {challenge[2]}, Unique: {challenge[3]}\n"
            await ctx.send(challenge_str)
        else:
            await ctx.send("No challenges found in the database.")
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")

# Command to complete a challenge for a user
@bot.command(name='complete_challenge')
async def complete_challenge(ctx, user_mention, challenge_id):
    try:
        # Check if the command user is the server owner
        if ctx.author.id != ctx.guild.owner_id:
            await ctx.send("Only the server owner can use this command.")
            return

        # Parse the user mention to get the user ID
        user_id = int(user_mention.strip('<@!>').replace('>', ''))

        # Complete the challenge for the user
        db.complete_challenge(user_id, challenge_id)

        # Retrieve the user's total points after completing the challenge
        user_points = db.get_user_points(user_id)

        await ctx.send(f"Challenge with ID {challenge_id} completed for user <@{user_id}>. "
                       f"They now have {user_points} points.")
    except ValueError:
        await ctx.send("Invalid user mention or challenge ID.")
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")

bot.run(TOKEN)