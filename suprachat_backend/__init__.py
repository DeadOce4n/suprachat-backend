import os
import logging

from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix

from . import db
from .blueprints.files import bp as files_bp
from .blueprints.user import bp as users_bp
from .utils import buntdb_to_mongodb


load_dotenv()


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    if __name__ != "__main__":
        gunicorn_logger = logging.getLogger('gunicorn.error')
        app.logger.handlers = gunicorn_logger.handlers
        app.logger.setLevel(gunicorn_logger.level)

    app.config.from_mapping(
        MONGO_URI=os.getenv("MONGO_URI"),
        SECRET_KEY=os.getenv("SECRET_KEY"),
        CORS_ALWAYS_SEND=True,
        CORS_ORIGINS="*",
        WEBIRCPASS=os.getenv("WEBIRC_PASSWORD"),
        UPLOAD_FOLDER=os.path.join(app.instance_path, "uploads"),
        MAX_CONTENT_LENGTH=int(os.getenv("MAX_CONTENT_LENGTH") or 3000000),
    )

    if test_config is None:
        app.config.from_pyfile("config.py", silent=True)
    else:
        app.config.from_mapping(test_config)

    try:
        os.makedirs(app.config["UPLOAD_FOLDER"])
    except OSError:
        pass

    CORS(app)
    db.mongo.init_app(app)
    db.init_app(app)
    buntdb_to_mongodb.init_app(app)
    app.register_blueprint(users_bp)
    app.register_blueprint(files_bp)

    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_host=1)

    return app
