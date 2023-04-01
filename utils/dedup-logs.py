""" dedup entries in price.logs where the price of a coin hasn't moved """
import argparse
import gzip
import logging
import sys
import traceback
from pathlib import Path

if __name__ == "__main__":
  