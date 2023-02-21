""" config-endpoint-service """
import argparse
import hashlib
import json
import os
import subprocess
import threading
import time
from datetime import datetime, timedelta
from typing import Any, Dict

import yaml
from flask import Flask, jsonify, Response

g: Dict[str, Any] = {}
app: Flask = Flask(__name__)


def log_msg(msg: str) -> None:
    """logs out message prefixed with timestamp"""
    now: str = datetime.now().strftime("%H:%M:%S")
    print(f"{now} {msg}")


def run_prove_backtesting() -> None:
    """calls prove-backtesting"""

    yesterday: datetime = datetime.now() - timedelta(days=1)
    end_date: str = yesterday.strftime("%Y%m%d")

    with open("configs/CONFIG_ENDPOINT_SERVICE.yaml", "w") as c:
        endpoint_config: dict[str, Any] = g["CONFIG"]
        endpoint_config["FROM_DATE"] = end_date
        endpoint_config["END_DATE"] = end_date
        # prove-backtestin won't take 0 but it doesn't matter as
        # we're giving yesterday's date as the start/end date and the logs
        # for today (ROLL_FORWARD=1) don't exist yet.
        endpoint_config["ROLL_FORWARD"] = int(1)
        c.write(json.dumps(endpoint_config))

    subprocess.run(
        "python -u utils/prove-backtesting.py "
        +