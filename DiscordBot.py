import discord
import os
from discord.ext import commands
from dotenv import load_dotenv
import DiscordDB
import random

# environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.members = True  # Disable typing events, if needed
intents.presences = True  # Disable presence events, if needed
intents.message_content = True    # Enable message content updates (required for commands)

bot = commands.Bot(command_prefix='!', intents=intents)
db = DiscordDB.DiscordDatabase()

# Define a dictionary to store active betting events
# WE WILL STORE THIS IN DB
active_betting_events = {}

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

@bot.command(name='list')
async def list_challenges(ctx):
    try:
        # Retrieve challenges from the database
        challenges_list = db.get_challenges()

        # Display challenges in a formatted way
        if challenges_list:
            challenge_str = "Challenges:\n"
            for challenge in challenges_list:
                challenge_str += f"ID: {challenge[0]}, Name: {challenge[1]}, Points: {challenge[2]}\n"
            await ctx.send(challenge_str)
        else:
            await ctx.send("No challenges found in the database.")
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")

@bot.command(name='completed_list')
async def completed_challenges(ctx):
    try:
        # Retrieve completed challenges from the database
        completed_challenges_list = db.get_completed_challenges()

        # Display completed challenges in a formatted way
        if completed_challenges_list:
            completed_str = "Completed Challenges:\n"
            for completion in completed_challenges_list:
                user_id, challenge_id, completion_count = completion
                challenge_info = db.get_challenge_info(challenge_id)  # Assuming there is a method to get challenge info by ID
                if challenge_info:
                    completed_str += (f"Challenge: {challenge_info['name']}, "
                                      f"User: <@{user_id}>, "
                                      f"Completion Count: {completion_count}\n")
                else:
                    completed_str += f"Challenge ID {challenge_id}, User: <@{user_id}>, Completion Count: {completion_count}\n"
            await ctx.send(completed_str)
        else:
            await ctx.send("No completed challenges found in the database.")
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")

# Command to complete a challenge for a user
@bot.command(name='complete')
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

# ================================= Betting ==================================== #
# Command to create a new betting event
@bot.command(name='create_event')
async def create_event(ctx, team1, team2, odds):
    try:
        guild_id = ctx.guild.id

        # Convert odds to a float (e.g., 2.5)
        odds = float(odds)

        # Initialize a new betting event
        event_id = ctx.message.id  # Using message ID as a unique event ID for simplicity
        db.create_event(guild_id, event_id, team1, team2, odds)

        # Add the event to the in-memory dictionary
        if guild_id not in active_betting_events:
            active_betting_events[guild_id] = []

        active_betting_events[guild_id].append({'event_id': event_id, 'team1': team1, 'team2': team2, 'odds': odds, 'bets': {}})

        await ctx.send(f"Betting event created! Event ID: {event_id}\n"
                       f"Teams: {team1} vs {team2}\n"
                       f"Odds: {odds}\n"
                       f"Place your bets using !bet {event_id} <team> <amount>")
    except ValueError:
        await ctx.send("Invalid odds. Please provide a valid floating-point number.")
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")

# Command to place a bet on a specific event
@bot.command(name='bet')
async def bet(ctx, event_id, chosen_team, amount):
    try:
        user_id = ctx.author.id
        guild_id = ctx.guild.id
        event_id = int(event_id)
        amount = int(amount)

        # Check if the guild has any active events
        if guild_id not in active_betting_events or not any(event['event_id'] == event_id for event in active_betting_events[guild_id]):
            await ctx.send("Invalid event ID. Make sure the event is still active.")
            return

        # Check if the chosen team is valid
        if chosen_team not in [event['team1'] for event in active_betting_events[guild_id]] + [event['team2'] for event in active_betting_events[guild_id]]:
            await ctx.send("Invalid team. Choose a team from the active events.")
            return

        # Check if the user has enough points to place the bet
        user_points = db.get_user_points(user_id)
        if amount > user_points:
            await ctx.send("You don't have enough points to place that bet.")
            return

        # Record the bet in the in-memory dictionary and the database
        for event in active_betting_events[guild_id]:
            if event['event_id'] == event_id:
                event['bets'][user_id] = {'team': chosen_team, 'amount': amount}
                break

        db.place_bet(guild_id, event_id, user_id, chosen_team, amount)
        
        # Deduct points from the user's wallet
        db.update_user_points(user_id, -amount)

        await ctx.send(f"Bet placed! You bet {amount} points on {chosen_team}. Good luck!")
    except ValueError:
        await ctx.send("Invalid event ID or amount. Please provide valid integers.")
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")

# Command to end a betting event and declare the winner
@bot.command(name='end_event')
async def end_event(ctx, event_id, winner_team):
    try:
        guild_id = ctx.guild.id
        event_id = int(event_id)
        winner_team = winner_team.lower()  # Convert to lowercase for case-insensitive comparison

        # Check if the guild has any active events
        if guild_id not in active_betting_events or not any(event['event_id'] == event_id for event in active_betting_events[guild_id]):
            await ctx.send("Invalid event ID. Make sure the event is still active.")
            return

        # Check if the event has already been ended
        if 'winner' in active_betting_events[guild_id]:
            await ctx.send("This event has already been ended.")
            return

        # Set the winner and calculate payouts
        for event in active_betting_events[guild_id]:
            if event['event_id'] == event_id:
                event['winner'] = winner_team
                winning_odds = event['odds'] if winner_team == event['team1'] else 1 / event['odds']
                break

        # Get bets for the winning team
        winning_bets = {user_id: bet['amount'] for user_id, bet in event['bets'].items() if bet['team'].lower() == winner_team}

        # Calculate payouts and update user points in the database
        for user_id, amount in winning_bets.items():
            payout = int(amount * winning_odds)
            db.update_user_points(user_id, payout)
            await ctx.send(f"{ctx.guild.get_member(user_id).mention} You won {payout} points! Congratulations!")

        await ctx.send(f"The winner is {winner_team}! Payouts have been processed.")
    except ValueError:
        await ctx.send("Invalid event ID. Please provide a valid integer.")
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")

# ================================= Gambling =================================== #
@bot.command(name='50/50')
async def fifty_fifty(ctx, amount):
    try:
        user_id = ctx.author.id
        amount = int(amount)

        # Check if the user has enough points to place the bet
        user_points = db.get_user_points(user_id)
        if amount > user_points:
            await ctx.send("You don't have enough points to place that bet.")
            return

        # Simulate a bet outcome (you can replace this with your own logic)
        win = random.choice([True, False])

        # Update user points based on the bet outcome
        if win:
            db.update_user_points(user_id, amount)
            await ctx.send(f"Congratulations! You won {amount} points. Your total points: {user_points + amount}")
        else:
            db.update_user_points(user_id, -amount)
            await ctx.send(f"Oops! You lost {amount} points. Your total points: {user_points - amount}")
    except ValueError:
        await ctx.send("Invalid bet amount. Please provide a positive integer.")
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")

bot.run(TOKEN)