import asyncio

from discord.ext import commands
from toolz import curried
import currency
from models import User, Item
from models import Store as StoreModel
from utils import default, author, coins, number
from prodict import Prodict
from datetime import datetime


class Store(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = default.get("config.json")

    @commands.group(name="buy", aliases=['b'], invoke_without_command=True)
    async def _buy(self, ctx, item_name: str):
        """ Buy an item from store """
        user = await author.get(ctx.author)
        item = Item.find_one({'name': item_name})
        if not item:
            return await ctx.send(f'```fix\nCannot find item "{item_name}"\n```')

        item = Prodict.from_dict(item)

        if any(i['id'] == item.id for i in user.item_list):
            return await ctx.send(f'```fix\nYou already own item "{item_name}"\n```')

        if user['quote_to'] != 'USD':
            rates = await coins.rate_convert()
            item.price = rates[user['quote_to']] * item.price
            item.payout = rates[user['quote_to']] * item.payout

        if user.game.in_pocket < item.price:
            return await ctx.send(f'```fix\nYou don\'t have enough money in your pocket\n```')

        user.game.in_pocket = round(user.game.in_pocket - item.price)
        user.item_list.append({
            'id': item.id,
            'last_run': datetime.now()
        })

        User.save(user)
        await ctx.send(f'```css\nYou bought an item\n```')

    @_buy.group(name="coin", aliases=['c'], invoke_without_command=True)
    async def buy_coin(self, ctx, amount: float, symbol: str):
        """ Buy coins for your game portfolio. """
        if ctx.invoked_subcommand is None:
            user = await author.get(ctx.author)
            mention = ctx.author.mention
            coin_prices = await coins.get_coins(user['quote_to'])
            if user['game']['in_pocket'] < amount:
                return await ctx.send(f'```fix\nYou don\'t have enough money in your pocket\n```')
            coin = list(filter(lambda c: c['symbol'] == symbol.upper(), coin_prices))
            if not coin:
                return await ctx.send(f'```fix\nCould not find coin "{symbol.upper()}"\n```')
            multiple = False
            if len(coin) > 1:
                multiple = True
                cn_list = ''
                for i in range(len(coin)):
                    cn_list += f'\n{i + 1}. {coin[i]["name"]}'
                cn_list += '\nType quit or cancel (q, c) to cancel the buy'
                await ctx.send(
                    f'```diff\nMore than one coin with symbol "{symbol.upper()}" please select one:\n{cn_list}\n```')

                def pred(m):
                    return m.author == ctx.message.author and m.channel == ctx.message.channel

                try:
                    msg = await self.bot.wait_for('message', check=pred, timeout=15.0)
                    selected_coin = msg.content
                except asyncio.TimeoutError:
                    return await ctx.send(f'```fix\nYou took too long...\n```{mention}')
                else:
                    if selected_coin in ['quit', 'cancel', 'q', 'c']:
                        return await ctx.send(f'```fix\nYou cancelled the buy\n```{mention}')
                    if not selected_coin.isdigit() or (int(selected_coin) - 1) not in range(len(coin)):
                        return await ctx.send(f'```fix\nInvalid selection\n```{mention}')

                    coin[0] = coin[int(selected_coin) - 1]

            if amount < 0.01:
                return await ctx.send(f'```fix\nAmount must be greater than 0.01\n```')
            coin = coin[0]
            coin_amount = 0
            price = float('{0:.8f}'.format(coin['quotes'][user['quote_to']]['price']))
            coin_amount = float('{0:.8f}'.format(amount / price))
            pcoin = coins.portfolio_has(user, symbol.upper(), coin['name'])
            if not pcoin:
                user['game']['portfolio']['coins'].append({
                    'symbol': coin['symbol'],
                    'name': coin['name'],
                    'amount': coin_amount,
                    'cost': amount,
                })
            else:
                k = pcoin['key']
                user['game']['portfolio']['coins'][k]['amount'] += coin_amount
                user['game']['portfolio']['coins'][k]['cost'] += amount

            user['game']['portfolio']['transactions'].append({
                'symbol': coin['symbol'],
                'name': coin["name"],
                'amount': coin_amount,
                'cost': amount,
                'coin_price': float('{0:.8f}'.format(coin['quotes'][user['quote_to']]['price'])),
                'created_at': datetime.now()
            })

            user['game']['in_pocket'] = user['game']['in_pocket'] - amount
            User.save(user)
            await ctx.send(
                f'```css\nYou bought {format(coin_amount, ".8f")} {symbol.upper()}{" - " + coin["name"] if multiple else ""}\n```')

    @buy_coin.command(name="all", aliases=['a'])
    async def buy_coin_all(self, ctx, symbol: str):
        """ Buy coin using remaining balance in your pocket """
        user = await author.get(ctx.author)
        mention = ctx.author.mention
        coin_prices = await coins.get_coins(user['quote_to'])
        if user.game.in_pocket <= 0:
            return await ctx.send(f'```fix\nYou don\'t have any money in your pocket\n```')
        coin = list(filter(lambda c: c['symbol'] == symbol.upper(), coin_prices))
        if not coin:
            return await ctx.send(f'```fix\nCould not find coin "{symbol.upper()}"\n```')
        multiple = False
        if len(coin) > 1:
            multiple = True
            cn_list = ''
            for i in range(len(coin)):
                cn_list += f'\n{i + 1}. {coin[i]["name"]}'
            cn_list += '\nType quit or cancel (q, c) to cancel the buy'
            await ctx.send(
                f'```diff\nMore than one coin with symbol "{symbol.upper()}" please select one:\n{cn_list}\n```')

            def pred(m):
                return m.author == ctx.message.author and m.channel == ctx.message.channel

            try:
                msg = await self.bot.wait_for('message', check=pred, timeout=15.0)
                selected_coin = msg.content
            except asyncio.TimeoutError:
                return await ctx.send(f'```fix\nYou took too long...\n```{mention}')
            else:
                if selected_coin in ['quit', 'cancel', 'q', 'c']:
                    return await ctx.send(f'```fix\nYou cancelled the buy\n```{mention}')
                if not selected_coin.isdigit() or (int(selected_coin) - 1) not in range(len(coin)):
                    return await ctx.send(f'```fix\nInvalid selection\n```{mention}')

                coin[0] = coin[int(selected_coin) - 1]

        coin = coin[0]
        coin_amount = 0
        price = float('{0:.8f}'.format(coin['quotes'][user.quote_to]['price']))
        coin_amount = float('{0:.8f}'.format(user.game.in_pocket / price))
        pcoin = coins.portfolio_has(user, symbol.upper(), coin["name"])
        if not pcoin:
            user['game']['portfolio']['coins'].append({
                'symbol': coin['symbol'],
                'name': coin['name'],
                'amount': coin_amount,
                'cost': user.game.in_pocket,
            })
        else:
            k = pcoin['key']
            user['game']['portfolio']['coins'][k]['amount'] += coin_amount
            user['game']['portfolio']['coins'][k]['cost'] += user.game.in_pocket

        user['game']['portfolio']['transactions'].append({
            'symbol': coin['symbol'],
            'name': coin['name'],
            'amount': coin_amount,
            'cost': user.game.in_pocket,
            'coin_price': float('{0:.8f}'.format(coin['quotes'][user['quote_to']]['price'])),
            'created_at': datetime.now()
        })

        user['game']['in_pocket'] = 0
        User.save(user)
        await ctx.send(
            f'```css\nYou bought {format(coin_amount, ".8f")} {symbol.upper()}{" - " + coin["name"] if multiple else ""}\n```')

    @commands.group(name="sell", aliases=['s'], invoke_without_command=True)
    async def _sell(self, ctx, item_name: str):
        """ Sell an item from store """
        user = await author.get(ctx.author)

        await ctx.send(f'```css\nSelling items coming soon\n```')

    @_sell.group(name="coin", aliases=['c'], invoke_without_command=True)
    async def sell_coin(self, ctx, amount: float, symbol: str):
        """ Sell a coin for your game portfolio. """
        if ctx.invoked_subcommand is None:
            user = await author.get(ctx.author)
            mention = ctx.author.mention
            coin_prices = await coins.get_coins(user['quote_to'])
            has_dupes = coins.portfolio_check_for_dupes(user, symbol.upper())
            if len(has_dupes) > 1:
                cn_list = ''
                for i in range(len(has_dupes)):
                    cn_list += f'\n{i + 1}. {has_dupes[i]}'
                cn_list += '\nType quit or cancel (q, c) to cancel the sell'
                await ctx.send(
                    f'```diff\nMore than one coin with symbol "{symbol.upper()}" please select one:\n{cn_list}\n```')

                def pred(m):
                    return m.author == ctx.message.author and m.channel == ctx.message.channel

                try:
                    msg = await self.bot.wait_for('message', check=pred, timeout=15.0)
                    selected = msg.content
                except asyncio.TimeoutError:
                    return await ctx.send(f'```fix\nYou took too long...\n```{mention}')
                else:
                    if selected in ['quit', 'cancel', 'q', 'c']:
                        return await ctx.send(f'```fix\nYou cancelled the sell\n```{mention}')
                    if not selected.isdigit() or (int(selected) - 1) not in range(len(has_dupes)):
                        return await ctx.send(f'```fix\nInvalid selection\n```{mention}')
                    coin = list(
                        filter(lambda c: c['symbol'] == symbol.upper() and c['name'] == has_dupes[int(selected) - 1],
                               coin_prices))
            elif len(has_dupes) > 0:
                coin = list(filter(lambda c: c['symbol'] == symbol.upper() and c['name'] == has_dupes[0], coin_prices))
            else:
                return await ctx.send(f'```fix\nCould not find coin "{symbol.upper()}"\n```{mention}')

            if not coin:
                return await ctx.send(f'```fix\nCould not find coin "{symbol.upper()}"\n```')
            multiple = False

            coin = coin[0]
            pcoin = coins.portfolio_has(user, symbol.upper(), coin["name"])
            if not pcoin:
                return await ctx.send(
                    f'```fix\nYou do not hold any {symbol.upper()}{" - " + coin["name"] if multiple else ""}\n```')

            k = pcoin['key']
            total_holdings = user['game']['portfolio']['coins'][k]['amount']
            if amount > user['game']['portfolio']['coins'][k]['amount']:
                return await ctx.send(
                    f'```fix\nYou are trying to sell more "{symbol.upper()}" than you hold.  Amount: {total_holdings}\n```')

            sorted_transactions = sorted(user['game']['portfolio']['transactions'], key=lambda t: t['coin_price'],
                                         reverse=True)
            cost_deductions = 0
            earned = 0
            amount_left = amount
            keys_to_delete = []
            # iterate over transactions until sell amount is fulfilled
            for i, tx in enumerate(sorted_transactions):
                if amount_left <= 0:
                    continue
                if tx['symbol'] == symbol.upper() and tx['name'] == coin[
                    'name']:
                    if tx['amount'] <= amount_left:
                        cost_deductions += tx['cost']
                        amount_left -= tx['amount']
                        keys_to_delete.append(i)
                    else:
                        tx['amount'] -= amount_left
                        tx['cost'] -= amount_left * tx['coin_price']
                        cost_deductions += amount_left * tx['coin_price']
                        amount_left = 0
                sorted_transactions[i] = tx
            for ele in keys_to_delete:
                del sorted_transactions[ele]
            user['game']['portfolio']['transactions'] = sorted_transactions
            user['game']['portfolio']['coins'][k]['amount'] -= amount
            user['game']['portfolio']['coins'][k]['cost'] -= cost_deductions
            if user['game']['portfolio']['coins'][k]['amount'] <= 0:
                del user['game']['portfolio']['coins'][k]
            earned = number.round_up(coin['quotes'][user['quote_to']]['price'] * amount, 2)
            user['game']['in_pocket'] += earned
            User.save(user)
            await ctx.send(
                f'```css\nYou sold {amount} {symbol.upper()}{" - " + coin["name"] if len(has_dupes) > 1 else ""} for {currency.symbol(user["quote_to"])}{earned}\n```')

    @sell_coin.command(name="all", aliases=['a'])
    async def sell_coin_all(self, ctx, symbol: str):
        """ Sell all of your portfolio holdings for a specific coin """
        user = await author.get(ctx.author)
        mention = ctx.author.mention
        coin_prices = await coins.get_coins(user['quote_to'])
        has_dupes = coins.portfolio_check_for_dupes(user, symbol.upper())
        if len(has_dupes) > 1:
            cn_list = ''
            for i in range(len(has_dupes)):
                cn_list += f'\n{i + 1}. {has_dupes[i]}'
            cn_list += '\nType quit or cancel (q, c) to cancel the sell'
            await ctx.send(
                f'```diff\nMore than one coin with symbol "{symbol.upper()}" please select one:\n{cn_list}\n```')

            def pred(m):
                return m.author == ctx.message.author and m.channel == ctx.message.channel

            try:
                msg = await self.bot.wait_for('message', check=pred, timeout=15.0)
                selected = msg.content
            except asyncio.TimeoutError:
                return await ctx.send(f'```fix\nYou took too long...\n```{mention}')
            else:
                if selected in ['quit', 'cancel', 'q', 'c']:
                    return await ctx.send(f'```fix\nYou cancelled the sell\n```{mention}')
                if not selected.isdigit() or (int(selected) - 1) not in range(len(has_dupes)):
                    return await ctx.send(f'```fix\nInvalid selection\n```{mention}')
                coin = list(
                    filter(lambda c: c['symbol'] == symbol.upper() and c['name'] == has_dupes[int(selected) - 1],
                           coin_prices))
        elif len(has_dupes) > 0:
            coin = list(filter(lambda c: c['symbol'] == symbol.upper() and c['name'] == has_dupes[0], coin_prices))
        else:
            return await ctx.send(f'```fix\nCould not find coin "{symbol.upper()}"\n```{mention}')

        if not coin:
            return await ctx.send(f'```fix\nCould not find coin "{symbol.upper()}"\n```{mention}')

        coin = coin[0]
        pcoin = coins.portfolio_has(user, symbol.upper(), coin["name"])
        if not pcoin:
            return await ctx.send(f'```fix\nYou do not hold any "{symbol.upper()}"\n```{mention}')

        k = pcoin['key']
        total_holdings = user['game']['portfolio']['coins'][k]['amount']
        earned = coin['quotes'][user['quote_to']]['price'] * total_holdings
        user['game']['in_pocket'] += round(earned)
        tx_del_ids = []
        for i in range(len(user['game']['portfolio']['transactions'])):
            if user['game']['portfolio']['transactions'][i]['symbol'] == symbol.upper() and \
                    user['game']['portfolio']['transactions'][i]['name'] == coin['name']:
                tx_del_ids.append(i)
        for ele in sorted(tx_del_ids, reverse=True):
            del user['game']['portfolio']['transactions'][ele]
        del user['game']['portfolio']['coins'][k]
        User.save(user)
        await ctx.send(
            f'```css\nYou sold {total_holdings} {symbol.upper()}{" - " + coin["name"] if len(has_dupes) > 1 else ""} for {"{0:.2f}".format(earned)}\n```{mention}')

    @commands.command(aliases=['v'])
    async def view(self, ctx, store=None):
        """ View store """
        user = await author.get(ctx.author)
        store_list = ''
        stores = StoreModel.find()
        loaded_store = None
        if store is None:
            if not stores:
                return await ctx.send(f'```fix\nThere are no stores setup"\n```')
            if stores.count() == 1:
                loaded_store = Prodict.from_dict(stores[0])
                item_list = ''
                for i, item in enumerate(loaded_store.inventory):
                    item = Prodict.from_dict(item)
                    if user['quote_to'] != 'USD':
                        rates = await coins.rate_convert()
                        item.price = rates[user['quote_to']] * item.price
                        item.payout = rates[user['quote_to']] * item.payout
                    formatted_price = currency.symbol(user["quote_to"]) + '{0:.2f}'.format(item.price)
                    formatted_payout = "{0:.2f}".format(item.payout)
                    item_list += f'{i + 1}. {item.name}{" " * (18 - len(item.name))}{formatted_price}{" " * (10 - len(formatted_price))}{item.about.format(payout=formatted_payout)}\n'
                return await ctx.send(
                    f'```py\n{user.quote_to}\n{loaded_store.name}\n\nItem{" " * (21 - len("item"))}Price{" " * (10 - len("price"))}Description\n\n{item_list}```')
            for i, _store in enumerate(stores):
                _store = Prodict.from_dict(_store)
                item_count = len(_store.inventory)
                store_list += f'\n{i + 1}. {_store.name}{" " * (12 - len("Name"))}{item_count}{" " * (10 - len(str(item_count)))}{_store.about}'
            store_list_head = f'\nName{" " * (15 - len("Name"))}Item Count{" " * (10 - len("item"))}Description'

            await ctx.send(f'```diff\nStore list:\n{store_list_head}{store_list}\n```')
            return await ctx.send_help('view')

        store_list = []
        for i, _store in enumerate(stores):
            store_list.append(_store)
        if store.isnumeric():
            if int(store) - 1 in range(len(store_list)):
                loaded_store = store_list[int(store) - 1]
        else:
            loaded_store = StoreModel.find_one({'name': store})

        if not loaded_store:
            return await ctx.send(f'```fix\nCould not find store "{store}"\n```')

        loaded_store = Prodict.from_dict(loaded_store)
        item_list = ''
        for i, item in enumerate(loaded_store.inventory):
            item = Prodict.from_dict(item)
            if user['quote_to'] != 'USD':
                rates = await coins.rate_convert()
                item.price = rates[user['quote_to']] * item.price
                item.payout = rates[user['quote_to']] * item.payout
            formatted_price = currency.symbol(user["quote_to"]) + '{0:.2f}'.format(item.price)
            formatted_payout = "{0:.2f}".format(item.payout)

            item_list += f'{i + 1}. {item.name}{" " * (18 - len(item.name))}{formatted_price}{" " * (10 - len(formatted_price))}{item.about.format(payout=formatted_payout)}\n'
        await ctx.send(
            f'```py\n{user.quote_to}\n{loaded_store.name}\n\nItem{" " * (21 - len("item"))}Price{" " * (10 - len("price"))}Description\n\n{item_list}```')


def setup(bot):
    bot.add_cog(Store(bot))
