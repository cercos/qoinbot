import os
import json

import aiohttp
from coinpaprika import client as Coinpaprika
import redis
from prodict import Prodict
from toolz import curried
import currency
from urllib3.exceptions import NewConnectionError

from utils import http, default

cache = redis.Redis(host=os.getenv('REDIS_HOST'), port=os.getenv('REDIS_PORT'), db=0)
api = Coinpaprika.Client()
config = default.get("config.json")
available_quote_currencies = 'USD, EUR, PLN, KRW, GBP, CAD, JPY, RUB, TRY, NZD, AUD, CHF, HKD, SGD, PHP, MXN, BRL, THB, CNY, CZK, DKK, HUF, IDR, ILS, INR, MYR, NOK, SEK, ZAR, ISK'


def format_number(number):
    return "{:,}".format(number)


def percent(a, b):
    result = 100 * (b - a) / a
    return result


async def rate_convert(from_currency='USD'):
    url = f'https://api.exchangeratesapi.io/latest?base={from_currency}'
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            r = await response.json()
            return r['rates']


def sort_coins(coins, sort_key, sort_dir, quote):
    _coins = []
    if sort_key == 'change':
        sort_key = 'percent_change_24h'
    reverse = True
    if sort_dir == 'desc':
        reverse = False
    for coin in coins:
        if type(coin) is dict:
            if type(coin['quotes'][quote]['price']) and type(
                    coin['quotes'][quote]['percent_change_24h']) is float:
                _coins.append(coin)
    return sorted(_coins, key=curried.get_in(['quotes', quote, sort_key]), reverse=reverse)


async def _fetch(url):
    return await http.get(url, res_method='json')


async def portfolio_value(user, coin_list):
    value = 0
    if user['game']['portfolio']['coins']:
        for coin in user['game']['portfolio']['coins']:
            coin = Prodict.from_dict(coin)
            value += await get_value(coin.symbol, user['quote_to'], coin.name, coin.amount, coin_list)
    return value


async def get_value(base, quote, name, amount, coin_list):
    value = None
    for coin in coin_list:
        if base == coin['symbol'] and name == coin['name']:
            value = coin['quotes'][quote]['price'] * amount

    return value


def portfolio_check_for_dupes(user, symbol, ptype: str = 'coins'):
    names = []
    for i, el in enumerate(user['game']['portfolio'][ptype]):
        if el['symbol'] == symbol:
            names.append(el['name'])
    names = list(set(names))
    return names


def portfolio_has(user, symbol, name, ptype: str = 'coins'):
    for i, el in enumerate(user['game']['portfolio'][ptype]):
        if el['symbol'] == symbol and el["name"] == name:
            return {'key': i}
    return False


async def get_coins(quote='USD'):
    coins = cache.get('coins-' + quote.lower())
    if not coins:
        print('hit api')
        coins = api.tickers(quotes=quote)
        cache.set('coins-' + quote.lower(), json.dumps(coins), ex=config.cache.coins)
    else:
        coins = json.loads(coins)
    return coins


async def valid_symbols(symbols):
    available_currencies = cache.get('valid-symbols')
    if not available_currencies:
        available_currencies = api.coins()
        cache.set('valid-symbols', json.dumps(available_currencies), ex=config.cache.valid_symbols)
    else:
        available_currencies = json.loads(available_currencies)
    valid_symbol_list = [d['symbol'] for d in available_currencies]
    return list(set(valid_symbol_list) & set(symbols))


async def valid_quote(quote):
    if quote in available_quote_currencies.split(', '):
        return True
    return False


async def generate_chart(ctx, symbols: str, quote: str, sort_key='percent_change_24h', sort_dir='asc'):
    chart = ''
    coins = await get_coins(quote)
    coins = sort_coins(coins, sort_key, sort_dir, quote)
    for coin in coins:
        if coin['symbol'] in symbols:
            priceint = float(coin['quotes'][quote]['price'])
            decimal_places = '{0:.6f}' if quote not in ['BTC', 'ETH'] else '{0:.8f}'
            price = format_number(
                float('{0:.2f}'.format(priceint) if priceint > 1 else decimal_places.format(priceint)))
            change = '{0:.2f}'.format(float(coin['quotes'][quote]['percent_change_24h']))
            chart += '\n{color}{symbol}{symbol_spacing}{currency_symbol}{price}{price_spacing}%{change}'.format(
                color='+' if float(change) >= 0 else '-',
                change=change,
                price=str(price),
                symbol=coin['symbol'] or 'N/A',
                currency_symbol=currency.symbol(quote),
                symbol_spacing=' ' * (8 - int(len(coin['symbol']))),
                price_spacing=' ' * (14 - int(len(price)))
            )

    return chart


async def convert_user_currency(user, rates, currency_symbol: str):
    user['quote_to'] = currency_symbol.upper()
    user['game']['money'] = rates[currency_symbol.upper()] * user['game']['money']
    user['game']['in_pocket'] = rates[currency_symbol.upper()] * user['game']['in_pocket']
    for i in range(len(user['game']['portfolio']['coins'])):
        user['game']['portfolio']['coins'][i]['cost'] = rates[currency_symbol.upper()] * \
                                                        user['game']['portfolio']['coins'][i]['cost']
    for i in range(len(user['game']['portfolio']['transactions'])):
        user['game']['portfolio']['transactions'][i]['cost'] = rates[currency_symbol.upper()] * \
                                                               user['game']['portfolio']['transactions'][i]['cost']
        user['game']['portfolio']['transactions'][i]['coin_price'] = rates[currency_symbol.upper()] * \
                                                                     user['game']['portfolio']['transactions'][i][
                                                                         'coin_price']
    return user
