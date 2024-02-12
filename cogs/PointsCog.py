from discord.ext import commands

class PointsCog(commands.Cog):
    def __init__(self, bot, db):
        self.bot = bot
        self.db = db

@commands.command(name='points')
async def check_points(self, ctx):
    # Check and display user points
    user_id = str(ctx.author.id)
    points = self.db.get_user_points(user_id)
    await ctx.send(f"{ctx.author.mention}, you have {points} points.")

@commands.command(name='leaderboard')
async def leaderboard(self, ctx):
    # Display the top 10 players on the leaderboard
    sorted_users = self.db.get_top_users()
    leaderboard_message = "Leaderboard:\n"
    for idx, (user_id, points) in enumerate(sorted_users, start=1):
        member = ctx.guild.get_member(int(user_id))
        username = member.name if member else f"User not found ({user_id})"
        leaderboard_message += f"{idx}. {username}: {points} points\n"

    await ctx.send(leaderboard_message)

def setup(bot):
    bot.add_cog(PointsCog(bot))