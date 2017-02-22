# -*- coding: utf-8 -*-
"""
Helpers for providers that need special filtering
"""


# T411
def t411season(season):
    real_s = season + 967
    if season == 25:
        real_s = 994
    if 25 < season < 28:
        real_s = season + 966
    return real_s


def t411episode(episode):
    real_ep = 936
    if 8 < episode < 31:
        real_ep = episode + 937
    if 30 < episode < 61:
        real_ep = episode + 1057
    return real_ep
