import asyncio
from datetime import datetime, timedelta
import discord
from discord.ext import commands
from prodict import Prodict

from utils import default, author, repo, coins, number
from models import User, Store, Item


class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = default.get("config.json")

    @commands.command(name='balance', aliases=['bal'])
    async def balance(self, ctx):
        """ Check your balance """
        user = await author.get(ctx.author)
        money = user.game.money
        in_pocket = user.game.in_pocket
        invested = sum(c['cost'] for c in user.game.portfolio.coins)
        total = number.round_up(money + in_pocket + invested, 2)
        mention = ctx.author.mention
        await ctx.send(
            f'```py\nIn Pocket: {in_pocket}\nBank: {money}\nInvested: {"{0:.2f}".format(invested)}\nTotal: {total}\n\nQoins represent a USD value by default, the balances will convert depending upon what quote currency you have set on your account.  Use the "{self.config.prefix[0]}sq <currency symbol>" command to change it```{mention}')

    @commands.command(name='setquote', aliases=['sq'])
    async def set_quote(self, ctx, symbol):
        """ Set the quote currency prices are displayed in for your account.\n\nAvailable:\nUSD, EUR, PLN, KRW, GBP, CAD, JPY, RUB, TRY, NZD, AUD, CHF, HKD, SGD, PHP, MXN, BRL, THB, CNY, CZK, DKK, HUF, IDR, ILS, INR, MYR, NOK, SEK, ZAR, ISK """
        user = await author.get(ctx.author)
        if symbol.upper() == user['quote_to']:
            return await ctx.send(f'```fix\nAlready set to {symbol.upper()}\n```')
        rates = await coins.rate_convert(user['quote_to'])

        if not await coins.valid_quote(symbol.upper()) or not symbol.upper() in rates.keys():
            await ctx.send(f'```fix\nInvalid quote currency\n```')
            return await ctx.send(f'```\nAvailable quotes: {coins.available_quote_currencies}\n```')
        user = await coins.convert_user_currency(user, rates, symbol.upper())
        User.save(user)

        await ctx.send(f'```fix\nSet your quote currency to {symbol.upper()}\n```')

    @commands.command(aliases=['inv'])
    async def inventory(self, ctx):
        """ Check your item inventory """
        user = await author.get(ctx.author)
        mention = ctx.author.mention
        item_list = ''
        if user.inventory:
            for item in user.inventory:
                item = Prodict.from_dict(item)
                item_list += f'\'{item.name}\'\n'
        await ctx.send(
            f'```py\nInventory:\n{item_list}```{mention}')

    @commands.command(name="wage")
    async def wage(self, ctx):
        """ Spend your time in the wage cage and collect your ration.\n100 hours max accumulation per collection. """
        user = await author.get(ctx.author)
        now = datetime.now()
        diff = now - user.game.last_wage
        wage_multiplier = int((diff.seconds / 60 / 60))
        wage_earned = int(user.game.wage * wage_multiplier)
        minutes = float(60 - diff.seconds / 60)
        seconds = (minutes - int(minutes)) * 60
        if wage_multiplier < 1:
            return await ctx.send(
                f'```fix\nWagey wagey, you\'re in the cagey.  You can collect again in {int(minutes)}:{str(int(seconds)).zfill(2)}\n```{ctx.author.mention}')
        if wage_multiplier > 100:
            actual = wage_multiplier
            wage_multiplier = 100
            wage_earned = int(user.game.wage * wage_multiplier)

        user.game.in_pocket = int(user.game.in_pocket + wage_earned)
        user.game.last_wage = datetime.now()
        user.game.total_wages = wage_earned + user.game.total_wages if user.game.total_wages else 0
        User.save(user)

        await ctx.send(
            f'```diff\n+{wage_earned} {self.config.economy.currency_name} You were in the cage for {wage_multiplier if wage_multiplier < 100 else 100} hours.  You have to wait at least 1 hour to collect again.\n```{ctx.author.mention}')

    @commands.command(name="collect", aliases=['c'])
    async def collect(self, ctx):
        """ Collect Qoins generated from items """
        user = await author.get(ctx.author)
        now = datetime.now()
        total_earned = 0
        item_earned = ''
        for i, item in enumerate(user.item_list):
            _item = Prodict.from_dict(Item.find_one({"_id": item['id']}))

            if item['last_run'] is None:
                earned = int(_item.payout)
                item_earned += f'\n+{earned} {self.config.economy.currency_name} - {_item.name}'
                total_earned += earned
                user.item_list[i]['last_run'] = datetime.now()
            else:
                diff = now - item['last_run']
                wage_multiplier = int((diff.seconds / 60))
                if wage_multiplier < _item.rate:
                    wait_time = _item.rate - wage_multiplier
                    item_earned += f'\n{_item.name} - not ready {wait_time} minutes left'
                    continue
                earned = int(_item.payout * wage_multiplier)
                item_earned += f'\n+{earned} {self.config.economy.currency_name} - {_item.name}'
                total_earned += earned
                user.item_list[i]['last_run'] = datetime.now()

        user.game.in_pocket = int(user.game.in_pocket + total_earned)
        User.save(user)

        await ctx.send(
            f'```diff\nTotal: {total_earned} {self.config.economy.currency_name}\n{item_earned}\n```{ctx.author.mention}')

    @commands.group(name="deposit", aliases=['dep'], invoke_without_command=True)
    async def _deposit(self, ctx, amount: float):
        """ Deposit pocket money into the bank account """
        if ctx.invoked_subcommand is None:
            user = await author.get(ctx.author)
            if not user.game.in_pocket:
                return await ctx.send(
                    f'```fix\nYou don\'t have any money in your pocket\n```{ctx.author.mention}')
            amount = number.round_down(amount, 2)
            if amount > user.game.in_pocket:
                return await ctx.send(
                    f'```fix\nYou don\'t have enough money in your pocket. Available: {user.game.in_pocket}\n```{ctx.author.mention}')
            user.game.money = user.game.money + amount
            user.game.in_pocket = user.game.in_pocket - amount
            User.save(user)

            await ctx.send(
                f'```diff\n+{amount} {self.config.economy.currency_name} were transferred to your bank account \n```{ctx.author.mention}')

    @_deposit.command(name="all", aliases=['a'])
    async def deposit_all(self, ctx):
        user = await author.get(ctx.author)
        pocket = user.game.in_pocket
        if not pocket:
            return await ctx.send(
                f'```fix\nYou don\'t have any money in your pocket\n```{ctx.author.mention}')
        user.game.in_pocket = 0
        user.game.money += pocket
        User.save(user)

        await ctx.send(
            f'```diff\n+{pocket} {self.config.economy.currency_name} were transferred to your bank account \n```{ctx.author.mention}')

    @commands.group(name="withdrawal", aliases=['with'], invoke_without_command=True)
    async def _withdrawal(self, ctx, amount: float):
        """ Withdrawal money from your bank account to your pocket """
        if ctx.invoked_subcommand is None:
            user = await author.get(ctx.author)
            if not user.game.money:
                return await ctx.send(
                    f'```fix\nYou don\'t have any money in the bank\n```{ctx.author.mention}')
            amount = number.round_down(amount, 2)
            if amount > user.game.money:
                return await ctx.send(
                    f'```fix\nYou don\'t have enough money in your bank. Available: {user.game.money}\n```{ctx.author.mention}')
            user.game.in_pocket = user.game.in_pocket + amount
            user.game.money = user.game.money - amount
            User.save(user)

            await ctx.send(
                f'```diff\n+{amount} {self.config.economy.currency_name} transferred to your pocket\n```{ctx.author.mention}')

    @_withdrawal.command(name="all", aliases=['a'])
    async def withdrawal_all(self, ctx):
        user = await author.get(ctx.author)
        money = user.game.money
        if not money:
            return await ctx.send(
                f'```fix\nYou don\'t have any money in the bank\n```{ctx.author.mention}')
        user.game.money = 0
        user.game.in_pocket += money
        User.save(user)

        await ctx.send(
            f'```diff\n+{money} {self.config.economy.currency_name} transferred to your pocket\n```{ctx.author.mention}')

    @commands.command(name='give')
    async def give(self, ctx, amount: float, user: discord.Member):
        """ Give a user Qoins from your account """
        giver = await author.get(ctx.author)
        receiver = User.find_one({'user_id': str(user.id)})
        if not receiver:
            return await ctx.send(f'```fix\nCannot find user\n```')
        if giver['game']['in_pocket'] < amount:
            return await ctx.send(f'```fix\nYou don\'t have enough money in your pocket\n```')
        giver['game']['in_pocket'] -= amount
        receiver['game']['in_pocket'] += amount
        User.save(giver)
        User.save(receiver)
        await ctx.send(f'```css\nYou gave {receiver["name"]} {amount} {self.config.economy.currency_name}\n```')

    @commands.group(name='create', aliases=['make'])
    @commands.check(repo.is_owner)
    async def _create(self, ctx):
        """ Create operations """
        if ctx.invoked_subcommand is None:
            await ctx.send_help("bank")

    @_create.command(name="store", aliases=['s'])
    @commands.check(repo.is_owner)
    async def create_store(self, ctx, name: str):
        """ Create a store """
        store = Store.find_one({'name': name})
        if not store:
            store = Store.insert_one({'name': name})
            return await ctx.send(f'```css\nCreated store "{name}"\n```')
        await ctx.send(f'```fix\nA store already exists with that name\n```')

    @_create.command(name="item", aliases=['i'])
    @commands.check(repo.is_owner)
    async def create_item(self, ctx, name: str, about: str, price: int, rate: int, payout: int):
        """ Create an item """
        item = Item.insert_one({
            'name': name,
            'about': about,
            'price': price,
            'rate': rate,
            'payout': payout
        })
        if not item:
            return await ctx.send(f'```fix\nThere was an error creating the item "{name}"\n```')

        await ctx.send(f'```css\nCreated the item "{name}"\n```')

    @commands.group(name='delete')
    @commands.check(repo.is_owner)
    async def _delete(self, ctx):
        """ Delete operations """
        if ctx.invoked_subcommand is None:
            await ctx.send_help("bank")

    @_delete.command(name="item", aliases=['i'])
    @commands.check(repo.is_owner)
    async def delete_item(self, ctx, name: str):
        """ Create an item """
        if not Item.delete_one({'name': name}):
            return await ctx.send(f'```fix\nThere was a problem deleting item "{name}"\n```')

        await ctx.send(f'```css\nDeleted the item "{name}"\n```')

    @commands.group(name='items')
    @commands.check(repo.is_owner)
    async def items(self, ctx):
        """ View items """
        items = Item.find()
        item_list = ''
        for item in items:
            item = Prodict.from_dict(item)
            item_list += f'{item.name} - {item.about}\nprice: {item.price} payout: {item.payout} rate: {item.rate}\n\n'
        await ctx.send(f'```py\nItems:\n{item_list}```')

    @commands.group(name='store')
    @commands.check(repo.is_owner)
    async def _store(self, ctx):
        """ Store operations """
        if ctx.invoked_subcommand is None:
            await ctx.send_help("store")

    @_store.command(name="stock")
    @commands.check(repo.is_owner)
    async def store_stock(self, ctx, store_name: str, item_name: str):
        store = Store.find_one({'name': store_name})
        if not store:
            return await ctx.send(f'```fix\nCould not find store "{store_name}"\n```')
        item = Item.find_one({'name': item_name})
        if not item:
            return await ctx.send(f'```fix\nCould not find item "{item_name}"\n```')

        store = Prodict.from_dict(store)
        item = Prodict.from_dict(item)
        if store.item_list:
            if item.id in store['item_list']:
                return await ctx.send(f'```fix\nItem "{item_name}" already exists in "{store_name}"\n```')
            store.item_list.append(item.id)
            print('exist')
        else:
            print('not exist')
            store.item_list = [item.id]

        Store.save(store)

        await ctx.send(f'```css\nStocked "{item_name}" in "{store_name}"\n```')

    @commands.group(name='bestow')
    @commands.check(repo.is_owner)
    async def _bestow(self, ctx, user: discord.Member, amount: float):
        user = User.find_one({'user_id': str(user.id)})
        user['game']['money'] += amount
        User.save(user)
        await ctx.send(
            f'```css\n{amount} {self.config.economy.currency_name} has been bestowed upon {user["name"]}\n```')

    @commands.group(name='reset')
    @commands.check(repo.is_owner)
    async def _reset(self, ctx, user: discord.Member):
        user = User.find_one({'user_id': str(user.id)})
        user['item_list'] = []
        user['game'] = {
            'in_pocket': 0,
            'money': self.config.economy.start_money,
            'wage': self.config.economy.start_wage,
            'last_wage': datetime.now() - timedelta(hours=1),
            'portfolio': {
                'coins': [],
                'transactions': []
            }
        }
        await ctx.send('```\nAre you sure you want to reset user? (y/n)\n```')

        def pred(m):
            return m.author == ctx.message.author and m.channel == ctx.message.channel

        try:
            msg = await self.bot.wait_for('message', check=pred, timeout=15.0)
            confirm = msg.content
        except asyncio.TimeoutError:
            return await ctx.send(f'```fix\nYou took too long...\n```')
        else:
            if confirm in ['yes', 'y']:
                User.save(user)
                return await ctx.send(f'```css\nReset user "{user["name"]}"\n```')
            else:
                return await ctx.send(f'```fix\nCanceled reset"\n```')


def setup(bot):
    bot.add_cog(Economy(bot))
