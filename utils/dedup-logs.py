""" dedup entries in price.logs where the price of a coin hasn't moved """
import argparse
import gzip
import logging
import sys
import traceback
from pathlib import Path

if __name__ == "__main__":
    try:
        parser = argparse.ArgumentParser()
        parser.add_argument("-l", "--log", help="log")
        args = parser.parse_args()

        p = Path(".")

        coin = {}
        oldcoin = {}
        w