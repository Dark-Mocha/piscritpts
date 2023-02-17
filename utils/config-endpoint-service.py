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
  