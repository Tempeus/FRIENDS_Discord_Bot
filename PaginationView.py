import discord
from discord.ext import commands

class PaginationView(discord.ui.View):
    current_page : int = 0

    async def send(self, ctx):
        self.message = await ctx.send(view=self)
        await self.update_message(self.data[self.current_page])

    def create_bet_events_embed(self, data):
        embed = discord.Embed(title=f"Betting Event #{data['event_id']}", color=discord.Color.blue())
        embed.add_field(name="Teams", value=f"{data['team1']} vs. {data['team2']}", inline=False)
        embed.add_field(name="Odds", value=f"{data['odds1']} : {data['odds2']}", inline=False)
        embed.add_field(name="Betting period ends", value=f"<t:{data['unix_timestamp']}:f> or <t:{data['unix_timestamp']}:R>", inline=False)
        embed.add_field(name=f"Bets on {data['team1']}", value='\n'.join([f'{user} ({amount} points)' for user, amount in data['team1_bets_with_usernames']]))
        embed.add_field(name=f"Bets on {data['team2']}", value='\n'.join([f'{user} ({amount} points)' for user, amount in data['team2_bets_with_usernames']]))

        embed.set_footer(text=f"Your Wallet Balance: {data['user_balance']} points")

        return embed

    async def update_message(self, data):
        self.update_buttons()
        await self.message.edit(embed=self.create_bet_events_embed(data), view=self)

    def update_buttons(self):
        if self.current_page == 0:
            self.first_page_button.disabled = True
            self.prev_button.disabled = True
            self.first_page_button.style = discord.ButtonStyle.gray
            self.prev_button.style = discord.ButtonStyle.gray
        else:
            self.first_page_button.disabled = False
            self.prev_button.disabled = False
            self.first_page_button.style = discord.ButtonStyle.green
            self.prev_button.style = discord.ButtonStyle.primary

        if self.current_page == int(len(self.data)):
            self.next_button.disabled = True
            self.last_page_button.disabled = True
            self.last_page_button.style = discord.ButtonStyle.gray
            self.next_button.style = discord.ButtonStyle.gray
        else:
            self.next_button.disabled = False
            self.last_page_button.disabled = False
            self.last_page_button.style = discord.ButtonStyle.green
            self.next_button.style = discord.ButtonStyle.primary

    def get_current_page_data(self):
        return self.data[self.current_page]


    @discord.ui.button(label="|<",
                       style=discord.ButtonStyle.green)
    async def first_page_button(self, interaction:discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.current_page = 0
        await self.update_message(self.get_current_page_data())

    @discord.ui.button(label="<",
                       style=discord.ButtonStyle.primary)
    async def prev_button(self, interaction:discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        if self.current_page > 0:
            self.current_page -= 1
        await self.update_message(self.get_current_page_data())

    @discord.ui.button(label=">",
                       style=discord.ButtonStyle.primary)
    async def next_button(self, interaction:discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        max_len = len(self.data)
        print(max_len)
        print(self.current_page)
        if self.current_page < max_len - 1:
            self.current_page += 1
        await self.update_message(self.get_current_page_data())

    @discord.ui.button(label=">|",
                       style=discord.ButtonStyle.green)
    async def last_page_button(self, interaction:discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.current_page = int(len(self.data))
        await self.update_message(self.get_current_page_data())