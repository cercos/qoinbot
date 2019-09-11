from discord.ext import commands
from utils import default, coins, author
from models import User


class Crypto(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = default.get("config.json")

    @commands.command(aliases=['p'])
    async def price(self, ctx, *, symbols):
        """ Returns a price for provided cryptocurrency symbols """
        user = await author.get(ctx.author)
        width = '\t' * 3
        mention = ctx.author.mention
        chart = await coins.generate_chart(ctx, symbols.upper().split(' '), user['quote_to'])
        chart = f'```diff\n{user["quote_to"]}{chart}{width}```{mention}'
        await ctx.send(chart)

    @commands.group(name='pricelist', aliases=['pl'], pass_context=True)
    async def _price_list(self, ctx):
        """ View the prices of coins you have saved into your price list"""
        if ctx.invoked_subcommand is None:
            user = await author.get(ctx.author)
            if not user['price_list']['coins']:
                await ctx.send(f'```fix\nYour price list is empty```')
                return await ctx.send_help("pricelist add")
            width = '\t' * 3
            mention = ctx.author.mention
            chart = await coins.generate_chart(ctx, user['price_list']['coins'], user['quote_to'], 'percent_change_24h',
                                               'asc')
            chart = f'```diff\n{user["quote_to"]}{chart}{width}```{mention}'
            await ctx.send(chart)

    @_price_list.command(name='add', aliases=['a'])
    async def price_list_add(self, ctx, *, symbols):
        """ Add coins to your price list """
        user = await author.get(ctx.author)
        new_coins = await coins.valid_symbols(symbols.upper().split(' '), user)
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

    @commands.command(aliases=['sq'])
    async def set_quote(self, ctx, symbol):
        """ Set the value coins are quoted in for your price requests.\n\nAvailable:\nUSD, EUR, PLN, KRW, GBP, CAD, JPY, RUB, TRY, NZD, AUD, CHF, HKD, SGD, PHP, MXN, BRL, THB, CNY, CZK, DKK, HUF, IDR, ILS, INR, MYR, NOK, SEK, ZAR, ISK """
        user = await author.get(ctx.author)
        if symbol.upper() == user['quote_to']:
            return await ctx.send(f'```fix\nAlready set to {symbol.upper()}\n```')
        rates = await coins.rate_convert(user['quote_to'])

        if not await coins.valid_quote(symbol.upper()) or not symbol.upper() in rates.keys():
            await ctx.send(f'```fix\nInvalid quote currency\n```')
            return await ctx.send(f'```\nAvailable quotes: {coins.available_quote_currencies}\n```')
        user['quote_to'] = symbol.upper()
        user['game']['money'] = rates[symbol.upper()] * user['game']['money']
        user['game']['in_pocket'] = rates[symbol.upper()] * user['game']['in_pocket']
        for i in range(len(user['game']['portfolio']['coins'])):
            user['game']['portfolio']['coins'][i]['cost'] = rates[symbol.upper()] * \
                                                            user['game']['portfolio']['coins'][i]['cost']
        for i in range(len(user['game']['portfolio']['transactions'])):
            user['game']['portfolio']['transactions'][i]['cost'] = rates[symbol.upper()] * \
                                                                   user['game']['portfolio']['transactions'][i]['cost']
            user['game']['portfolio']['transactions'][i]['coin_price'] = rates[symbol.upper()] * \
                                                                         user['game']['portfolio']['transactions'][i][
                                                                             'coin_price']
        User.save(user)

        await ctx.send(f'```fix\nSet your quote currency to {symbol.upper()}\n```')


def setup(bot):
    bot.add_cog(Crypto(bot))
