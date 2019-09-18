import asyncio
from datetime import datetime
from discord.ext import commands
from prodict import Prodict
import currency
from toolz import curried

from utils import default, author, coins, repo
from models import User
from millify import millify


class Game(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = default.get("config.json")

    @commands.group(name='portfolio', aliases=['po'], invoke_without_command=True)
    async def _portfolio(self, ctx, page: int = 1):
        """ Check your portfolio """
        if ctx.invoked_subcommand is None:
            user = await author.get(ctx.author)
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

                if page > page_count:
                    return
                user.game.portfolio.coins = pcoins[page - 1]
            if user.game.portfolio.coins:
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

                portfolio_info = f'Value: {total_value}\nInvested: {total_cost}\n{percent_color}%Change: %{percent_change}\n\nIn Pocket: {in_pocket}\nBank: {in_bank}\nNet worth: {portfolio_value}'

                table_header = f'Symbol{" " * (8 - len("Symbol"))}Holdings{" " * (12 - len("Holdings"))}Value{" " * (10 - len("Value"))}%Change'
                mention = ctx.author.mention
                await ctx.send(
                    f'```diff\n{user["quote_to"]}\n{table_header}\n{portfolio}\n{" " * 15}Page {page} of {page_count}\n\n{portfolio_info}```{mention}')
                return
            await ctx.send(f'```fix\nYou don\'t have any coins in your portfolio```')
            return await ctx.send_help('buy coin')

    @_portfolio.command(aliases=['h'])
    async def holding(self, ctx, symbol: str):
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
    async def whalelist(self, ctx, page: int = 1):
        """ View the whalelist (leaderboard) """
        owners = default.get("config.json").owners
        user = await author.get(ctx.author)
        per_page = self.config.game.whalelist_per_page
        page_count = 1
        coin_list = await coins.get_coins(user['quote_to'])
        whales = User.find()
        whales = sorted(whales, key=curried.get_in(['game', 'money']), reverse=True)
        if len(whales) > per_page:
            whales = default.divide_chunks(whales, per_page)[page - 1]
            page_count = len(whales)
        whale_list = ''
        if page > page_count:
            return
        for doc in whales:
            if int(doc['user_id']) not in owners:
                if doc['quote_to'] != user['quote_to']:
                    rates = await coins.rate_convert(doc['quote_to'])
                    doc = await coins.convert_user_currency(doc, rates, user['quote_to'])
                doc_pvalue = 0
                for coin in doc['game']['portfolio']['coins']:
                    doc_pvalue += await coins.get_value(coin['symbol'], doc['quote_to'], coin['name'], coin['amount'], coin_list)
                doc_total = currency.symbol(user["quote_to"]) + '{0:.2f}'.format(
                    doc["game"]["money"] + doc["game"]["in_pocket"] + doc_pvalue)
                whale_list += f'\n{doc["name"]}{" " * (25 - len(doc["name"]))}{doc_total}'

        await ctx.send(f'```\nBiggest whales:\n{user["quote_to"]}\n{whale_list}\n\nPage {page} of {page_count}```')


def setup(bot):
    bot.add_cog(Game(bot))
