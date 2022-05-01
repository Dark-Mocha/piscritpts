""" price_log_service.py """
from flask import send_from_directory, Flask

app: Flask = Flask(__name__)


@app.route("/<path:path>")
d