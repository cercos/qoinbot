from discord.ext import commands
from utils import default, coins, author
from models import User


class Crypto(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = default.get("config.json")

    @commands.command(aliases=['p'])
    @commands.cooldown(rate=1, per=5.0, type=commands.BucketType.user)
    async def price(self, ctx, *, symbols):
        """ Returns a price for provided cryptocurrency symbols """
        user = await author.get(ctx.author)
        width = '\t' * 3
        mention = ctx.author.mention
        message = await ctx.send(f'```Fetching prices...```')
        chart = await coins.generate_chart(ctx, symbols.upper().split(' '), user['quote_to'])
        chart = f'```diff\n{user["quote_to"]}{chart}{width}```{mention}'
        await message.edit(content=chart)

    @commands.group(name='pricelist', aliases=['pl'], pass_context=True, invoke_without_command=True)
    @commands.cooldown(rate=1, per=5.0, type=commands.BucketType.user)
    async def _price_list(self, ctx, page: int = 1):
        """ View the prices of coins you have saved into your price list"""
        if ctx.invoked_subcommand is None:
            user = await author.get(ctx.author)
            if not user['price_list']['coins']:
                await ctx.send(f'```fix\nYour price list is empty```')
                return await ctx.send_help("pricelist add")

            # per_page = self.config.game.pricelist_per_page
            # page_count = 1
            # price_list = user['price_list']['coins']
            # if len(price_list) > per_page:
            #     price_list = [price_list[i:i + per_page] for i in range(0, len(price_list), per_page)]
            #     page_count = len(price_list)
            #
            #     if page > page_count or page < 1:
            #         return
            #     user['price_list']['coins'] = price_list[page - 1]

            mention = ctx.author.mention
            message = await ctx.send(f'```Fetching prices...```')
            chart = await coins.generate_chart(ctx, user['price_list']['coins'], user['quote_to'], 'percent_change_24h',
                                               'asc')

            chart = f'```diff\n{user["quote_to"]}{chart}```{mention}'
            # chart = f'```diff\n{user["quote_to"]}{chart}\nPage {page} of {page_count}```{mention}'
            await message.edit(content=chart)

    @_price_list.command(name='add', aliases=['a'])
    async def price_list_add(self, ctx, *, symbols):
        """ Add coins to your price list """
        user = await author.get(ctx.author)
        new_coins = await coins.valid_symbols(symbols.upper().split(' '))
        filtered_coins = [x for x in new_coins if x not in user['price_list']['coins']]

        if user['price_list']['coins']:
            new_coins = filtered_coins + user['price_list']['coins']

        user['price_list']['coins'] = new_coins
        User.save(user)

        width = '\t' * 3
        mention = ctx.author.mention
        chart = await coins.generate_chart(ctx, user['price_list']['coins'], user['quote_to'], 'percent_change_24h',
                                           'asc')
        chart = f'```diff\n{user["quote_to"]}{chart}{width}```{mention}'
        await ctx.send(f'```css\nAdded {", ".join(map(str, filtered_coins))} to your price list\n```{chart}')

    @_price_list.command(name='delete', aliases=['d', 'del', 'rm'])
    async def price_list_delete(self, ctx, *, symbols):
        """ Deletes coins from your price list """
        user = await author.get(ctx.author)

        if not user['price_list']['coins']:
            await ctx.send(f'```fix\nYour price list is empty```')
            return await ctx.send_help("price list add")
        new_coins = [x for x in user['price_list']['coins'] if x not in symbols.upper().split(' ')]
        user['price_list']['coins'] = new_coins if len(new_coins) > 0 else []
        User.save(user)

        width = '\t' * 3
        mention = ctx.author.mention
        chart = await coins.generate_chart(ctx, user['price_list']['coins'], user['quote_to'], 'percent_change_24h',
                                           'asc')
        chart = f'```diff\n{user["quote_to"]}{chart}{width}```{mention}'
        await ctx.send(f'```css\nDeleted coins from your price list\n```{chart}')

    @_price_list.command(name='clear', aliases=['nuke'])
    async def price_list_clear(self, ctx):
        """ Clears all coins from your price list """
        user = await author.get(ctx.author)
        if not user['price_list']['coins']:
            await ctx.send(f'```fix\nYour price list is empty```')
            return await ctx.send_help("price list add")
        user['price_list']['coins'] = []
        User.save(user)
        await ctx.send('```css\nCleared your price list\n```')


def setup(bot):
    bot.add_cog(Crypto(bot))
