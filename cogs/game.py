from datetime import datetime
from discord.ext import commands
from prodict import Prodict
import currency
from toolz import curried

from utils import default, author, coins
from models import User
from millify import millify


class Game(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = default.get("config.json")

    @commands.group(name='portfolio', aliases=['po'], invoke_without_command=True)
    async def _portfolio(self, ctx, holding: str = None):
        """ Check your portfolio """
        if ctx.invoked_subcommand is None:
            if holding is None:
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

                        formatted_holdings = millify(coin.amount, precision=8 if coin.amount < 100 else 3)
                        formatted_percent = millify(percent_change, precision=2)
                        formatted_value = millify(value, precision=2)

                        color = '+' if percent_change >= 0 else '-'
                        portfolio += f'{color}{coin.symbol}{" " * (7 - len(coin.symbol))}{formatted_holdings}{" " * (12 - len(formatted_holdings))}{currency.symbol(user["quote_to"])}{formatted_value}{" " * (7 - len(formatted_value))}%{formatted_percent}\n'

                percent_change = coins.percent(total_cost, total_value)
                percent_color = '+' if percent_change >= 0 else '-'
                total_value = currency.symbol(user["quote_to"]) + '{0:.2f}'.format(total_value)
                total_cost = currency.symbol(user["quote_to"]) + '{0:.2f}'.format(total_cost)
                percent_change = '{0:.2f}'.format(percent_change)
                in_bank = currency.symbol(user["quote_to"]) + '{0:.2f}'.format(user['game']['money'])
                in_pocket = currency.symbol(user["quote_to"]) + '{0:.2f}'.format(user['game']['in_pocket'])

                portfolio_info = f'Value: {total_value}\nInvested: {total_cost}\n{percent_color}%Change: %{percent_change}\n\nBank: {in_bank}\nIn Pocket: {in_pocket}'

                table_header = f'Symbol{" " * (8 - len("Symbol"))}Holdings{" " * (12 - len("Holdings"))}Value{" " * (8 - len("Value"))}%Change'
                mention = ctx.author.mention
                await ctx.send(
                    f'```diff\n{user["quote_to"]}\n{table_header}\n{portfolio}\n{portfolio_info}```{mention}')
            else:
                user = await author.get(ctx.author)
                if not coins.valid_symbols([holding.upper()]):
                    return await ctx.send(f'```fix\nInvalid symbol```')
                if not any(d['symbol'] == holding.upper() for d in user.game.portfolio.transactions):
                    return await ctx.send(f'```fix\nYou don\'t hold any {holding.upper()}```')
                transactions = [item for item in user.game.portfolio.transactions if item['symbol'] == holding.upper()]
                tx_list = ''
                for tx in transactions:
                    formatted_amount = '{0:.8f}'.format(tx["amount"])
                    formatted_cost = '{0:.2f}'.format(tx["cost"])
                    formatted_price = currency.symbol(user['quote_to']) + '{0:.6f}'.format(tx["coin_price"])
                    tx_list += f'\n{formatted_amount}{" " * (20 - len(formatted_amount))}{formatted_cost}{" " * (12 - len(formatted_cost))}{formatted_price}'

                table_header = f'\nAmount{" " * (20 - len("Amount"))}Cost{" " * (12 - len("Cost"))}Price'
                await ctx.send(f'```diff\nTransactions for {holding.upper()}:\n{table_header}\n{tx_list}\n```')

    @commands.command(aliases=['wl', 'lb'])
    async def whalelist(self, ctx):
        """ View the whalelist (leaderboard) """
        whales = User.find()
        whales = sorted(whales, key=curried.get_in(['game', 'money']), reverse=True)
        whale_list = ''
        for doc in whales:
            whale_list += f'\n{doc["name"]}{" " * (25 - len(doc["name"]))}{doc["game"]["money"] + doc["game"]["in_pocket"]}'

        await ctx.send(f'```\nBiggest whales:\n{whale_list}```')


def setup(bot):
    bot.add_cog(Game(bot))
