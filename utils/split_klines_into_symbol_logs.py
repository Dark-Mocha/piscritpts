""" splits klines logfiles into individual symbol files """

import argparse
import gzip
import os

from typing import Dict

parser = argparse.ArgumentParser()
parser.add_argument("-f")

args = parser.parse_args()
daylog = args.f

with gzip.open(daylog, "rt") as f:
    lines = f.readlines()

coins: Dict = {}
coin_filenames = set()
for line in lines:
    parts = line.split(" ")
    symbol = parts[2]
    price = parts[3]

    date = parts[0].replace("-", "")
    coin_filename = f"log/{symbol}/{date}.log"

    # if we already have a gzipped file for this coin, it means we've already
    # processed it, so skip it
    if os.path.exists(f"{coin_filename}.gz"):
        continue

    if symbol not in coins:
        coins[symbol] = {}
        coins[symbol]["lines"] = []
        coins[symbol]["oldprice"] = 0

    coins[symbol]["lines"].append(line)
 