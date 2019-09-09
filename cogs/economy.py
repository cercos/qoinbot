from datetime import datetime
from discord.ext import commands
from prodict import Prodict

from utils import default, author, repo, coins
from models import User, Store, Item


class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = default.get("config.json")

    @commands.command(name='balance', aliases=['bal'])
    async def balance(self, ctx):
        """ Check your balance """
        user = await author.get(ctx.author)
        money = user['game']['money']
        in_pocket = user['game']['in_pocket']
        mention = ctx.author.mention
        await ctx.send(
            f'```py\nIn Pocket: {in_pocket}\nBank: {money}\nTotal: {money + in_pocket}\n\nQoins represent a USD value by default, the balances will convert depending upon what quote currency you have set on your account.  Use the "{self.config.prefix[0]}sq <currency symbol>" command to change it```{mention}')

    @commands.command(aliases=['inv'])
    async def inventory(self, ctx):
        """ Check your item inventory """
        user = await author.get(ctx.author)

        item_list = ''
        if user.inventory:
            for item in user.inventory:
                item = Prodict.from_dict(item)
                item_list += f'\'{item.name}\'\n'
        mention = ctx.author.mention
        await ctx.send(
            f'```py\nInventory:\n{item_list}```{mention}')

    @commands.command(name="wage")
    async def wage(self, ctx):
        """ Spend your time in the wage cage and collect your ration """
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

        user.game.in_pocket = int(user.game.in_pocket + wage_earned)
        user.game.last_wage = datetime.now()
        user.game.total_wages = wage_earned + user.game.total_wages
        User.save(user)

        await ctx.send(
            f'```diff\n+{wage_earned} {self.config.economy.currency_name} You were in the cage for {wage_multiplier} hours.  You have to wait at least 1 hour to collect again.\n```{ctx.author.mention}')

    @commands.command(name="deposit", aliases=['dep'])
    async def deposit(self, ctx, amount):
        """ Deposit pocket money into the bank account """
        user = await author.get(ctx.author)
        if not user.game.in_pocket:
            return await ctx.send(
                f'```fix\nYou don\'t have any money in your pocket\n```{ctx.author.mention}')
        if amount == 'all':
            amount = user.game.in_pocket
        if int(amount) > user.game.in_pocket:
            amount = user.game.in_pocket
        user.game.money = user.game.money + int(amount)
        user.game.in_pocket = user.game.in_pocket - int(amount)
        User.save(user)

        await ctx.send(
            f'```diff\n+{amount} {self.config.economy.currency_name} were transferred to your bank account \n```{ctx.author.mention}')

    @commands.command(name="withdrawal", aliases=['with'])
    async def withdrawal(self, ctx, amount):
        """ Withdrawal money from your bank account to your pocket """
        user = await author.get(ctx.author)
        if not user.game.money:
            return await ctx.send(
                f'```fix\nYou don\'t have any money in the bank\n```{ctx.author.mention}')
        if amount == 'all':
            amount = user.game.money
        amount = float(amount)
        if amount > user.game.money:
            amount = user.game.money
        user.game.in_pocket = int(user.game.in_pocket + amount)
        user.game.money = int(user.game.money - amount)
        User.save(user)

        await ctx.send(
            f'```diff\n+{amount} {self.config.economy.currency_name} transferred to your pocket\n```{ctx.author.mention}')

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
            store.item_list = store.item_list.append(item.id)
        else:
            store.item_list = [item.id]

        Store.save(store)

        await ctx.send(f'```css\nStocked "{item_name}" in "{store_name}\n```')


def setup(bot):
    bot.add_cog(Economy(bot))
