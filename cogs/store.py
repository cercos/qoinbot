from discord.ext import commands
from toolz import curried

from models import User, Item
from models import Store as StoreModel
from utils import default, author, coins
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
        if item.id in user.item_list:
            return await ctx.send(f'```fix\nYou already own item "{item_name}"\n```')
        item = Prodict.from_dict(item)
        total_cost = int(item.price)
        if user.game.in_pocket < total_cost:
            return await ctx.send(f'```fix\nYou don\'t have enough money in your pocket\n```')

        user.game.in_pocket = user.game.in_pocket - total_cost
        user.item_list.extend([item.id])
        User.save(user)
        await ctx.send(f'```css\nYou bought an item\n```')

    @_buy.command(name="coin", aliases=['c'])
    async def buy_coin(self, ctx, amount: int, symbol: str):
        """ Buy coins for your game portfolio. """
        user = await author.get(ctx.author)
        coin_prices = await coins.get_coins(user['quote_to'])
        if user['game']['in_pocket'] < amount:
            return await ctx.send(f'```fix\nYou don\'t have enough money in your pocket\n```')
        coin = list(filter(lambda c: c['symbol'] == symbol.upper(), coin_prices))
        if not coin:
            return await ctx.send(f'```fix\nCould not find coin "{symbol.upper()}"\n```')
        coin = coin[0]
        coin_amount = 0
        price = coin['quotes'][user['quote_to']]['price']
        coin_amount = amount / price
        pcoin = coins.portfolio_has(user, symbol.upper())
        if not pcoin:
            user['game']['portfolio']['coins'].append({
                'symbol': coin['symbol'],
                'amount': coin_amount,
                'cost': amount,
            })
        else:
            k = pcoin['key']
            user['game']['portfolio']['coins'][k]['amount'] += coin_amount
            user['game']['portfolio']['coins'][k]['cost'] += amount

        user['game']['portfolio']['transactions'].append({
            'symbol': coin['symbol'],
            'amount': coin_amount,
            'cost': amount,
            'coin_price': coin['quotes'][user['quote_to']]['price'],
            'created_at': datetime.now()
        })

        user['game']['in_pocket'] = user['game']['in_pocket'] - amount
        User.save(user)
        await ctx.send(f'```css\nYou bought {coin_amount} {symbol.upper()}\n```')

    @commands.group(name="sell", aliases=['s'], invoke_without_command=True)
    async def _sell(self, ctx, item_name: str):
        """ Sell an item from store """
        user = await author.get(ctx.author)
        # item = Item.find_one({'name': item_name})
        # if not item:
        #     return await ctx.send(f'```fix\nCannot find item "{item_name}"\n```')
        # if item.id in user.item_list:
        #     return await ctx.send(f'```fix\nYou already own item "{item_name}"\n```')
        # item = Prodict.from_dict(item)
        # total_cost = int(item.price)
        # if user.game.in_pocket < total_cost:
        #     return await ctx.send(f'```fix\nYou don\'t have enough money in your pocket\n```')
        #
        # user.game.in_pocket = user.game.in_pocket - total_cost
        # user.item_list.extend([item.id])
        # User.save(user)
        await ctx.send(f'```css\nYou sold an item\n```')

    @_sell.command(name="coin", aliases=['c'])
    async def sell_coin(self, ctx, amount: float, symbol: str):
        """ Sell coins for your game portfolio. """
        user = await author.get(ctx.author)
        coin_prices = await coins.get_coins(user['quote_to'])
        coin = list(filter(lambda c: c['symbol'] == symbol.upper(), coin_prices))
        pcoin = coins.portfolio_has(user, symbol.upper())
        if not pcoin:
            return await ctx.send(f'```fix\nYou do not hold any "{symbol.upper()}"\n```')

        k = pcoin['key']
        total_holdings = user['game']['portfolio']['coins'][k]['amount']
        if amount > user['game']['portfolio']['coins'][k]['amount']:
            return await ctx.send(
                f'```fix\nYou are trying to sell more "{symbol.upper()}" than you hold.  Amount: {total_holdings}\n```')

        sorted_transactions = sorted(user['game']['portfolio']['transactions'], key=lambda t: t['coin_price'],
                                     reverse=True)
        cost_deductions = 0
        amount_left = amount
        keys_to_delete = []
        # iterate over transactions until sell amount is fulfilled
        for i in range(len(sorted_transactions)):
            if sorted_transactions[i]['symbol'] == symbol.upper():
                if sorted_transactions[i]['amount'] <= amount_left:
                    print('less')
                    cost_deductions += sorted_transactions[i]['cost']
                    keys_to_delete.append(i)
                    amount_left -= sorted_transactions[i]['amount']
                else:
                    print('more')
                    sorted_transactions[i]['amount'] -= amount
                    sorted_transactions[i]['cost'] -= amount * sorted_transactions[i]['coin_price']
                    cost_deductions += amount * sorted_transactions[i]['coin_price']
                for ele in sorted(keys_to_delete, reverse=True):
                    del sorted_transactions[ele]
                user['game']['portfolio']['transactions'] = sorted_transactions
                user['game']['portfolio']['coins'][k]['amount'] -= amount
                user['game']['portfolio']['coins'][k]['cost'] -= cost_deductions
                if user['game']['portfolio']['coins'][k]['amount'] == 0:
                    del user['game']['portfolio']['coins'][k]
                earned = coin[0]['quotes'][user['quote_to']]['price'] * amount
                user['game']['in_pocket'] += round(earned)
                User.save(user)
                await ctx.send(f'```css\nYou sold {amount} {symbol.upper()} for {earned}\n```')

    @commands.command(aliases=['v'])
    async def view(self, ctx, store_name: str):
        """ View store """
        store = StoreModel.find_one({'name': store_name})

        if not store:
            return await ctx.send(f'```fix\nCould not find store "{store_name}"\n```')

        store = Prodict.from_dict(store)
        item_list = ''
        for item in store.inventory:
            item = Prodict.from_dict(item)
            item_list += f'{item.name}{" " * (15 - len(item.name))}{item.price}{" " * (10 - len(str(item.price)))}{item.payout}\n'
        await ctx.send(
            f'```css\n{store.name}\n\nitem{" " * (15 - len("item"))}price{" " * (10 - len("price"))}payout\n\n{item_list}```')


def setup(bot):
    bot.add_cog(Store(bot))
