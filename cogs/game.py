from datetime import datetime
from discord.ext import commands
from prodict import Prodict
import currency
from utils import default, author, coins


class Game(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = default.get("config.json")

    @commands.command(aliases=['po'])
    async def portfolio(self, ctx):
        """ Check your portfolio """
        user = await author.get(ctx.author)
        coin_list = await coins.get_coins(user['quote_to'])

        portfolio = ''
        total_value = 0
        total_cost = 0
        if user.game.portfolio.coins:
            for coin in user.game.portfolio.coins:
                coin = Prodict.from_dict(coin)
                value = await coins.get_value(coin.symbol, user['quote_to'], coin.amount, coin_list)
                total_value += value
                total_cost += coin.cost
                percent_change = coins.percent(coin['cost'], value)
                formatted_price = '{0:.8f}'.format(coin.amount)
                formatted_percent = '{0:.2f}'.format(percent_change)
                formatted_value = '{0:.2f}'.format(value)
                color = '+' if percent_change >= 0 else '-'
                portfolio += f'{color}{coin.symbol}{" " * (10 - len(coin.symbol))}{formatted_price}{" " * (16 - len(formatted_price))}{currency.symbol(user["quote_to"])}{formatted_value}{" " * (10 - len(formatted_value))}%{formatted_percent}\n'
        mention = ctx.author.mention
        total_value = '{0:.2f}'.format(total_value)
        total_cost = '{0:.2f}'.format(total_cost)
        portfolio_info = f'Value: {currency.symbol(user["quote_to"])}{total_value}\nInvested: {currency.symbol(user["quote_to"])}{total_cost}'
        await ctx.send(
            f'```diff\n{user["quote_to"]}:\n{portfolio}\n{portfolio_info}```{mention}')


def setup(bot):
    bot.add_cog(Game(bot))
