
""" retrieves klines for binance suitable for cryptoBot """

import argparse
import gzip
import os
import json
import time
from datetime import datetime, timedelta

from binance.client import Client  # pylint: disable=E0401

client = Client("FAKE", "FAKE")