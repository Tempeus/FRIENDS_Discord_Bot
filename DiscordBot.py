import discord
import os
from discord.ext import commands
from dotenv import load_dotenv
import DiscordDB
import random
import datetime

# environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.members = True  # Disable typing events, if needed
intents.presences = True  # Disable presence events, if needed
intents.message_content = True    # Enable message content updates (required for commands)

class CustomHelpCommand(commands.DefaultHelpCommand):
    async def send_bot_help(self, mapping):
        embed = discord.Embed(title="Friend Bot's Commands", color=discord.Color.blue())

        for cog, commands in mapping.items():
            if cog:
                embed.add_field(name=cog.qualified_name, value=" ".join(f"`{command.name}\n`" for command in commands), inline=False)
            else:
                embed.add_field(name="No Category", value=" ".join(f"`{command.name}\n`" for command in commands), inline=False)

        channel = self.get_destination()
        await channel.send(embed=embed)

    async def send_command_help(self, command):
        embed = discord.Embed(title=f"Help for `{command.name}`", description=command.help, color=discord.Color.green())
        channel = self.get_destination()
        await channel.send(embed=embed)


async def main():
    bot = commands.Bot(command_prefix='!', help_command=CustomHelpCommand(), intents=intents)
    db = DiscordDB.DiscordDatabase()

    # Load cogs
    initial_extensions = ['cogs.ChallengeCog']

    for extension in initial_extensions:
        await bot.load_extension(extension)

    @bot.event
    async def on_ready():
        db.create_tables()

    # ================================= Betting ==================================== #
    # Command to create a new betting event
    @bot.command(name='create_event')
    async def create_event(ctx, team1, team2, odds, duration_hours):
        try:
            guild_id = ctx.guild.id
            odds = float(odds)
            duration_hours = int(duration_hours)

            # Calculate the end time of the betting period
            betting_end_time = datetime.datetime.now() + datetime.timedelta(hours=duration_hours)

            # Create the event in the database
            event_id = db.create_event(guild_id, team1, team2, odds, betting_end_time)

            # Convert betting_end_time to Unix timestamp
            unix_timestamp = int(betting_end_time.timestamp())

            await ctx.send(f"Event ID: {event_id} created successfully! Betting duration ends at: <t:{unix_timestamp}:f> or <t:{unix_timestamp}:R>")
        except ValueError:
            await ctx.send("Invalid odds or duration. Please provide valid numbers.")
        except Exception as e:
            await ctx.send(f"An error occurred: {e}")

    # Command to place a bet
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

            # Check if the betting period has ended
            if datetime.datetime.now() > db.get_betting_end_time(guild_id, event_id):
                await ctx.send("Betting period has ended.")
                return

            # Place the bet in the database
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
            print(active_events)

            # Check if there are any active events
            if not active_events:
                await ctx.send("No active events available.")
                return

            # Format and send the list of active events in a Discord message
            event_list_message = "List of Active Events:\n"
            for event in active_events:
                event_id, team1, team2, odds, betting_end_time = event
                unix_timestamp  = int(datetime.datetime.strptime(betting_end_time, "%Y-%m-%d %H:%M:%S.%f").timestamp())
                event_list_message += f"Event ID: {event_id}, Teams: {team1} vs {team2} \nOdds: {odds} [Betting period ends at <t:{unix_timestamp}:f> or <t:{unix_timestamp}:R>]\n"

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

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
    #TODO: HELP METHOD