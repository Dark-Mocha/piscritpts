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
    price = parts[