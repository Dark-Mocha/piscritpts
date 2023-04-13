
""" prove backtesting """
import glob
import json
import os
import re
import subprocess
import sys
from argparse import ArgumentParser, Namespace
from datetime import datetime, timedelta
from itertools import islice
from multiprocessing import Pool
from string import Template
from time import sleep
from typing import Any, Dict, List, Optional, Set, Tuple

import pandas as pd
import requests
import yaml
from tenacity import retry, wait_exponential


@retry(wait=wait_exponential(multiplier=2, min=1, max=30))
def get_index_json(query: str) -> requests.Response:
    """retry wrapper for requests calls"""
    response: requests.Response = requests.get(query, timeout=5)
    status: int = response.status_code
    if status != 200:
        with open("log/price_log_service.response.log", "at") as l:
            l.write(f"{query} {status} {response}\n")
        response.raise_for_status()
    return response


def log_msg(msg: str) -> None:
    """logs out message prefixed with timestamp"""
    now: str = datetime.now().strftime("%H:%M:%S")
    print(f"{now} PROVE-BACKTESTING: {msg}")


def cleanup() -> None:
    """clean files"""
    for item in glob.glob("configs/coin.*.yaml"):
        os.remove(item)
    for item in glob.glob("results/backtesting.coin.*.txt"):
        os.remove(item)
    for item in glob.glob("results/backtesting.coin.*.log.gz"):
        os.remove(item)
    if os.path.exists("log/backtesting.log"):
        os.remove("log/backtesting.log")


def flag_checks() -> None:
    """checks for flags in control/"""
    while os.path.exists("control/PAUSE"):
        log_msg("control/PAUSE flag found. Sleeping 1min.")
        sleep(60)


def wrap_subprocessing(conf: str, timeout: Optional[int] = 0) -> None:
    """wraps subprocess call"""
    if timeout == 0:
        timeout = None
    subprocess.run(
        "python app.py -m backtesting -s tests/fake.yaml "
        + f"-c configs/{conf} >results/backtesting.{conf}.txt 2>&1",
        shell=True,
        timeout=timeout,
        check=False,
    )


class ProveBacktesting:
    """ProveBacktesting"""

    def __init__(self, cfg: Dict[str, Any]) -> None:
        """init"""
        self.min: float = float(cfg["MIN"])
        self.filter_by: str = cfg["FILTER_BY"]
        self.from_date: datetime = datetime.strptime(
            str(cfg["FROM_DATE"]), "%Y%m%d"
        )
        self.end_date: datetime = datetime.strptime(