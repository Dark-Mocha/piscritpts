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
    """calls pr