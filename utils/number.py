from math import floor, ceil
import decimal


def round_down(n, d=8):
    d = int('1' + ('0' * d))
    return floor(n * d) / d


def round_up(n, d=8):
    d = int('1' + ('0' * d))
    return ceil(n * d) / d


def human_format(num):
    num = float('{:.3g}'.format(num))
    magnitude = 0
    while abs(num) >= 1000:
        magnitude += 1
        num /= 1000.0
    return '{}{}'.format('{:f}'.format(num).rstrip('0').rstrip('.'), ['', 'K', 'M', 'B', 'T'][magnitude])
