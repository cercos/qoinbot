from math import floor, ceil
import decimal


def round_down(n, d=8):
    d = int('1' + ('0' * d))
    return floor(n * d) / d


def round_up(n, d=8):
    d = int('1' + ('0' * d))
    return ceil(n * d) / d


