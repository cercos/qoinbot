import asyncio
from datetime import datetime
from typing import Union

import discord
from discord.ext import commands
from discord.utils import get
from prodict import Prodict
import currency
from toolz import curried
import pprint
from utils import default, author, coins, repo
from models import User
from millify import millify
from PIL import Image, ImageDraw, ImageFont, ImageColor


class Game(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = default.get("config.json")

    @commands.group(name='portfolio', aliases=['po'], invoke_without_command=True)
    @commands.cooldown(rate=2, per=5.0, type=commands.BucketType.user)
    async def _portfolio(self, ctx, page: int = 1):
        """ Check your portfolio """
        if ctx.invoked_subcommand is None:
            user = await author.get(ctx.author)
            if not user.game.portfolio.coins:
                await ctx.send(f'```fix\nYou don\'t have any coins in your portfolio```')
                return await ctx.send_help('buy coin')
            message = await ctx.send(f'```Fetching prices...```')

            per_page = self.config.game.portfolio_per_page
            page_count = 1
            coin_list = await coins.get_coins(user['quote_to'])

            portfolio = ''
            total_value = await coins.portfolio_value(user, coin_list)
            total_cost = 0
            pcoins = user.game.portfolio.coins
            total_cost = sum(item['cost'] for item in pcoins)

            if len(pcoins) > per_page:
                pcoins = [pcoins[i:i + per_page] for i in range(0, len(pcoins), per_page)]
                page_count = len(pcoins)
                user.game.portfolio.coins = pcoins[page - 1]

            if page == 0 or page > page_count:
                # remove fetch message
                await message.delete()
                return

            for coin in user.game.portfolio.coins:
                coin = Prodict.from_dict(coin)

                value = await coins.get_value(coin.symbol, user['quote_to'], coin.name, coin.amount, coin_list)
                percent_change = coins.percent(coin['cost'], value)

                formatted_holdings = millify(coin.amount, precision=4)
                formatted_percent = millify(percent_change, precision=2)
                formatted_value = millify(value, precision=2)

                color = '+' if percent_change >= 0.00 else '-'
                portfolio += f'{color}{coin.symbol}{" " * (7 - len(coin.symbol))}{formatted_holdings}{" " * (12 - len(formatted_holdings))}{currency.symbol(user["quote_to"])}{formatted_value}{" " * (9 - len(formatted_value))}%{formatted_percent}\n'

            percent_change = coins.percent(total_cost, total_value)
            percent_color = '+' if percent_change >= 0.00 else '-'
            portfolio_value = currency.symbol(user['quote_to']) + '{0:.2f}'.format(
                total_value + user['game']['money'] + user['game']['in_pocket'])

            total_value = currency.symbol(user["quote_to"]) + '{0:.2f}'.format(total_value)
            total_cost = currency.symbol(user["quote_to"]) + '{0:.2f}'.format(total_cost)
            percent_change = '{0:.2f}'.format(percent_change)
            in_bank = currency.symbol(user["quote_to"]) + '{0:.2f}'.format(user['game']['money'])
            in_pocket = currency.symbol(user["quote_to"]) + '{0:.2f}'.format(user['game']['in_pocket'])

            portfolio_info = f'Value{" " * (15 - len("Value"))}Invested{" " * (12 - len("Value"))}%Change\n{total_value}{" " * (15 - len(str(total_value)))}{total_cost}{" " * (15 - len(str(total_cost)))}%{percent_change}'
            balance = f'In Pocket: {in_pocket}\nBank: {in_bank}\nNet worth: {portfolio_value}'
            table_header = f'Symbol{" " * (8 - len("Symbol"))}Holdings{" " * (12 - len("Holdings"))}Value{" " * (10 - len("Value"))}%Change'
            mention = ctx.author.mention
            return await message.edit(content=
                                      f'```diff\n{user["quote_to"]}\n{table_header}\n{portfolio}\n{" " * 15}Page {page} of {page_count}``````py\n{portfolio_info}\n``````py\n{balance}```{mention}')

    @_portfolio.command(name='user', aliases=['u'])
    @commands.cooldown(rate=1, per=5.0, type=commands.BucketType.user)
    async def portfolio_user(self, ctx, user: Union[discord.Member, str], page: int = 1):
        """ View another users portfolio """

        if not user == self.bot.user:
            if not type(user) is discord.Member:
                user = Prodict.from_dict(User.find_one({'name': user}))
            else:
                user = await author.get(user, False)
            if not user or not user.game.portfolio.coins:
                return await ctx.send(f'```fix\nUser has an empty portfolio```')

            message = await ctx.send(f'```Fetching prices...```')
            per_page = self.config.game.portfolio_per_page
            page_count = 1
            coin_list = await coins.get_coins(user['quote_to'])

            portfolio = ''
            total_value = await coins.portfolio_value(user, coin_list)
            total_cost = 0
            pcoins = user.game.portfolio.coins
            total_cost = sum(item['cost'] for item in pcoins)

            if len(pcoins) > per_page:
                pcoins = [pcoins[i:i + per_page] for i in range(0, len(pcoins), per_page)]
                page_count = len(pcoins)
                user.game.portfolio.coins = pcoins[page - 1]

            if page == 0 or page > page_count:
                await message.delete()
                return

            for coin in user.game.portfolio.coins:
                coin = Prodict.from_dict(coin)

                value = await coins.get_value(coin.symbol, user['quote_to'], coin.name, coin.amount, coin_list)
                percent_change = coins.percent(coin['cost'], value)

                formatted_holdings = millify(coin.amount, precision=4)
                formatted_percent = millify(percent_change, precision=2)
                formatted_value = millify(value, precision=2)

                color = '+' if percent_change >= 0.00 else '-'
                portfolio += f'{color}{coin.symbol}{" " * (7 - len(coin.symbol))}{formatted_holdings}{" " * (12 - len(formatted_holdings))}{currency.symbol(user["quote_to"])}{formatted_value}{" " * (9 - len(formatted_value))}%{formatted_percent}\n'

            percent_change = coins.percent(total_cost, total_value)
            percent_color = '+' if percent_change >= 0.00 else '-'
            portfolio_value = currency.symbol(user['quote_to']) + '{0:.2f}'.format(
                total_value + user['game']['money'] + user['game']['in_pocket'])

            total_value = currency.symbol(user["quote_to"]) + '{0:.2f}'.format(total_value)
            total_cost = currency.symbol(user["quote_to"]) + '{0:.2f}'.format(total_cost)
            percent_change = '{0:.2f}'.format(percent_change)
            in_bank = currency.symbol(user["quote_to"]) + '{0:.2f}'.format(user['game']['money'])
            in_pocket = currency.symbol(user["quote_to"]) + '{0:.2f}'.format(user['game']['in_pocket'])

            portfolio_info = f'Value: {total_value}\nInvested: {total_cost}\n{percent_color}%Change: %{percent_change}'
            balance = f'\nIn Pocket: {in_pocket}\nBank: {in_bank}\nNet worth: {portfolio_value}'
            table_header = f'Symbol{" " * (8 - len("Symbol"))}Holdings{" " * (12 - len("Holdings"))}Value{" " * (10 - len("Value"))}%Change'
            mention = ctx.author.mention
            return await message.edit(content=
                                      f'```{user.name}\'s Portfolio``````diff\n{user["quote_to"]}\n{table_header}\n{portfolio}\n{" " * 15}Page {page} of {page_count}``````diff\n{portfolio_info}\n``````py\n{balance}```{mention}')

    @_portfolio.command(name='holding', aliases=['h'])
    @commands.cooldown(rate=1, per=5.0, type=commands.BucketType.user)
    async def portfolio_holding(self, ctx, symbol: str):
        """ View a specific portfolio holding transactions"""
        user = await author.get(ctx.author)
        mention = ctx.author.mention

        if not await coins.valid_symbols([symbol.upper()]):
            return await ctx.send(f'```fix\nInvalid symbol```')
        if not any(d['symbol'] == symbol.upper() for d in user.game.portfolio.transactions):
            return await ctx.send(f'```fix\nYou don\'t hold any {symbol.upper()}```')
        has_dupes = coins.portfolio_check_for_dupes(user, symbol.upper())

        multiple = False
        if len(has_dupes) > 1:
            multiple = True
            cn_list = ''
            for i in range(len(has_dupes)):
                cn_list += f'\n{i + 1}. {has_dupes[i]}'
            await ctx.send(
                f'```diff\nPortfolio contains more than one coin with symbol "{symbol.upper()}" please select one:\n{cn_list}\n```{mention}')

            def pred(m):
                return m.author == ctx.message.author and m.channel == ctx.message.channel

            try:
                msg = await self.bot.wait_for('message', check=pred, timeout=15.0)
                selected_coin = msg.content
            except asyncio.TimeoutError:
                return await ctx.send(f'```fix\nYou took too long...\n```{mention}')
            else:
                if not selected_coin.isdigit() or (int(selected_coin) - 1) not in range(len(has_dupes)):
                    return await ctx.send(f'```fix\nInvalid selection\n```{mention}')
            transactions = [item for item in user.game.portfolio.transactions if
                            item['symbol'] == symbol.upper() and item['name'] == has_dupes[int(selected_coin) - 1]]
        else:
            transactions = [item for item in user.game.portfolio.transactions if item['symbol'] == symbol.upper()]
        tx_list = ''
        total_amount = 0
        coin_name = ''
        for tx in transactions:
            coin_name = tx['name']
            total_amount += float('{0:.8f}'.format(tx["amount"]))
            formatted_amount = millify(tx["amount"], precision=4)
            formatted_cost = currency.symbol(user['quote_to']) + millify(tx["cost"],
                                                                         precision=2 if tx['cost'] > 0 else 6)
            formatted_price = currency.symbol(user['quote_to']) + millify(tx["coin_price"],
                                                                          precision=2 if tx['coin_price'] > .01 else 6)
            tx_list += f'\n{formatted_amount}{" " * (12 - len(formatted_amount))}{formatted_cost}{" " * (12 - len(formatted_cost))}{formatted_price}'

        table_header = f'\nAmount{" " * (12 - len("Amount"))}Cost{" " * (12 - len("Cost"))}Price'
        await ctx.send(
            f'```diff\nTransactions for {symbol.upper()}{" - " + coin_name if multiple else ""}:\nTotal: {total_amount}\n{table_header}\n{tx_list}\n```{mention}')

    @commands.command(aliases=['wl', 'lb'])
    @commands.cooldown(rate=1, per=5.0, type=commands.BucketType.user)
    async def whalelist(self, ctx, page: int = 1):
        """ View the whalelist (leaderboard) """
        owners = default.get("config.json").owners
        user = await author.get(ctx.author)
        per_page = self.config.game.whalelist_per_page
        page_count = 1
        _whales = User.find()
        whales = []
        # add the networth to each user and remove users excluded from whale lists
        for i, doc in enumerate(_whales):
            if int(doc['user_id']) not in owners:
                if doc['name'] != self.bot.user.name:
                    coin_list = await coins.get_coins(user['quote_to'])

                    doc_pvalue = await coins.portfolio_value(doc, coin_list, user['quote_to'])
                    doc['game']['networth'] = float(
                        '{0:.2f}'.format(doc["game"]["money"] + doc["game"]["in_pocket"] + doc_pvalue))
                    whales.append(doc)
        whales = sorted(whales, key=curried.get_in(['game', 'networth']), reverse=True)
        if len(whales) > per_page:
            whales = default.divide_chunks(whales, per_page)[page - 1]
            page_count = len(whales)
        whale_list = ''
        if page > page_count:
            return
        for i, doc in enumerate(whales):
            rates = await coins.rate_convert(doc['quote_to'])
            doc = await coins.convert_user_currency(doc, rates, user['quote_to'])

            whale_list += f'\n{i + 1}. {doc["name"]}{" " * (25 - len(doc["name"]))}{currency.symbol(user["quote_to"])}{doc["game"]["networth"]}'
        await ctx.send(f'```py\n{user["quote_to"]}\nBiggest whales:\n{whale_list}\n\nPage {page} of {page_count}```')

    @commands.group(name='remove', aliases=['rem'])
    @commands.check(repo.is_owner)
    async def _remove(self, ctx):
        """ Remove operations """
        if ctx.invoked_subcommand is None:
            await ctx.send_help("remove")

    @_remove.command(name="user", aliases=['u'])
    @commands.check(repo.is_owner)
    async def remove_user(self, ctx, user: str):
        """ Remove a user """
        _user = User.find_one({'name': user})
        if not _user:
            return await ctx.send(f'```fix\nCannot find user with name "{user}"\n```')
        User.remove({'name': user})

        await ctx.send(f'```css\nRemoved the user "{user}"\n```')

def setup(bot):
    bot.add_cog(Game(bot))
