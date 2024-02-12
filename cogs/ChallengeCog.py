from discord.ext import commands

class ChallengeCog(commands.Cog):
    def __init__(self, bot, db):
        self.bot = bot
        self.db = db

    @commands.command(name='create_challenge')
    async def add_challenge(self, ctx, name, points, unique_challenge=True):
        try:
            points = int(points)
            if points < 0:
                raise ValueError("Points should be a non-negative integer.")

            # Add the challenge to the database
            self.db.add_challenge(name, points, unique_challenge)

            await ctx.send(f"Challenge '{name}' with {points} points added successfully.")
        except ValueError as ve:
            await ctx.send(f"Error: {ve}")
        except Exception as e:
            await ctx.send(f"An error occurred: {e}")

    @commands.command(name='challenges')
    async def list_challenges(self, ctx):
        try:
            # Retrieve challenges from the database
            challenges_list = self.db.get_challenges()

            # Display challenges in a formatted way
            if challenges_list:
                challenge_str = "Challenges:\n"
                for challenge in challenges_list:
                    challenge_str += f"ID: {challenge[0]}: {challenge[2]} point - {challenge[1]}\n"
                await ctx.send(challenge_str)
            else:
                await ctx.send("No challenges found in the database.")
        except Exception as e:
            await ctx.send(f"An error occurred: {e}")

    @commands.command(name='completed')
    async def completed_challenges(self, ctx):
        try:
            # Retrieve completed challenges from the database
            completed_challenges_list = self.db.get_completed_challenges()

            # Display completed challenges in a formatted way
            if completed_challenges_list:
                completed_str = "Completed Challenges:\n"
                for completion in completed_challenges_list:
                    user_id, challenge_id, completion_count = completion
                    challenge_info = self.db.get_challenge_info(challenge_id)  # Assuming there is a method to get challenge info by ID
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
    @commands.command(name='complete')
    async def complete_challenge(self, ctx, user_mention, challenge_id):
        try:
            # Check if the command user is the server owner
            if ctx.author.id != ctx.guild.owner_id:
                await ctx.send("Only the server owner can use this command.")
                return

            # Parse the user mention to get the user ID
            user_id = int(user_mention.strip('<@!>').replace('>', ''))

            # Complete the challenge for the user
            self.db.complete_challenge(user_id, challenge_id)

            # Retrieve the user's total points after completing the challenge
            user_points = self.db.get_user_points(user_id)

            await ctx.send(f"Challenge with ID {challenge_id} completed for user <@{user_id}>. "
                        f"They now have {user_points} points.")
        except ValueError:
            await ctx.send("Invalid user mention or challenge ID.")
        except Exception as e:
            await ctx.send(f"An error occurred: {e}")

def setup(bot, db):
    bot.add_cog(ChallengeCog(bot, db))