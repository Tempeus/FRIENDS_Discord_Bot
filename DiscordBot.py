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

@bot.command(name='challenges')
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

@bot.command(name='completed')
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
        odds = float(odds)

        # Create the event in the database
        event_id = db.create_event(guild_id, team1, team2, odds)
        await ctx.send(f"Event created successfully! Event ID: {event_id}")
    except ValueError:
        await ctx.send("Invalid odds. Please provide a valid float.")
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

        # Check if the event is still active in the database
        if not db.is_event_active(guild_id, event_id):
            await ctx.send("Invalid event ID. Make sure the event is still active.")
            return

        # Check if the chosen team is valid
        if not db.is_valid_team(guild_id, event_id, chosen_team):
            await ctx.send("Invalid team. Choose a team from the active events.")
            return

        # Check if the user has enough points to place the bet
        user_points = db.get_user_points(user_id)
        if amount > user_points:
            await ctx.send("You don't have enough points to place that bet.")
            return

        # Deduct points from the user's wallet
        db.update_user_points(user_id, -amount)

        # Record the bet in the database
        db.place_bet(guild_id, event_id, user_id, chosen_team, amount)

        await ctx.send(f"Bet placed! You bet {amount} points on {chosen_team}. Good luck!")
    except ValueError:
        await ctx.send("Invalid event ID or amount. Please provide valid integers.")
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")

# Command to end a betting event and declare the winner
@bot.command(name='end_event')
async def end_event(ctx, event_id, winner_team):
    try:
        user_id = ctx.author.id
        guild_id = ctx.guild.id
        event_id = int(event_id)

        # Check if the event is still active in the database
        if not db.is_event_active(guild_id, event_id):
            await ctx.send("Invalid event ID. Make sure the event is still active.")
            return

        # Check if the event has already been ended
        if db.is_event_ended(guild_id, event_id):
            await ctx.send("This event has already been ended.")
            return

        # Set the winner and calculate payouts
        winning_odds, winning_bets = db.calculate_payouts(guild_id, event_id, winner_team)
        print(winning_bets)

        # Update user points in the database
        for user_id, amount in winning_bets.items():
            print(str(user_id) + "bet this much: " + str(amount))
            payout = int(amount * winning_odds)
            db.update_user_points(user_id, payout + amount)
            await ctx.send(f"{ctx.guild.get_member(user_id).mention} You won {payout} points! Congratulations!")

        # Mark the event as ended in the database
        db.mark_event_as_ended(guild_id, event_id)

        await ctx.send(f"The winner is {winner_team}! Payouts have been processed.")
    except ValueError:
        await ctx.send("Invalid event ID. Please provide a valid integer.")
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")

# Command to display a list of events with user bets
@bot.command(name='events')
async def list_events(ctx):
    try:
        guild_id = ctx.guild.id

        # Retrieve the list of active events from the database
        active_events = db.get_active_events(guild_id)

        # Check if there are any active events
        if not active_events:
            await ctx.send("No active events available.")
            return

        # Format and send the list of active events in a Discord message
        event_list_message = "List of Active Events:\n"
        for event in active_events:
            event_id, team1, team2, odds = event
            event_list_message += f"Event ID: {event_id}, Teams: {team1} vs {team2}, Odds: {odds}\n"

            # Retrieve user bets for each team from the database
            team1_bets = db.get_bets_for_team(guild_id, event_id, team1)
            team2_bets = db.get_bets_for_team(guild_id, event_id, team2)

            # Convert user IDs to usernames
            team1_bets_with_usernames = [(ctx.guild.get_member(user_id).name, amount) for user_id, amount in team1_bets]
            team2_bets_with_usernames = [(ctx.guild.get_member(user_id).name, amount) for user_id, amount in team2_bets]

            # Append user bets information to the message
            event_list_message += f"\tBets on {team1}: {', '.join([f'{user} ({amount} points)' for user, amount in team1_bets_with_usernames])}\n"
            event_list_message += f"\tBets on {team2}: {', '.join([f'{user} ({amount} points)' for user, amount in team2_bets_with_usernames])}\n"

        await ctx.send(event_list_message)
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

# DEBUGGING
@bot.command(name="add")
async def add(ctx, amount):
    try:
        user_id = ctx.author.id
        amount = int(amount)

        db.update_user_points(user_id, amount)
        await ctx.send("sent " + str(amount))
    except ValueError:
        await ctx.send("Invalid user ID or points. Please provide valid integers.")
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")

bot.run(TOKEN)


#TODO: HELP METHOD