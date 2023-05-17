""" splits klines logfiles into individual symbol files """

import argparse
import gzip
import os

from typing import Dict

parser = argparse.ArgumentParser()
parser.add_argument("-f")

args = parser.parse_