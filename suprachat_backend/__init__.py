import os
from flask import Flask
from flask_cors import CORS

from . import db
from .views.user import bp as users_bp
from .views.files import bp as files_bp
from .utils import buntdb_to_mongodb
from werkzeug.middleware.proxy_fix import ProxyFix


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        MONGO_URI="mongodb://localhost:27017/suprachat",
        SECRET_KEY="dev",
        CORS_ALWAYS_SEND=True,
        CORS_ORIGINS="*",
        WEBIRCPASS="contraseña",
        UPLOAD_FOLDER=os.path.join(app.instance_path, "uploads"),
        MAX_CONTENT_LENGTH=3 * 1000 * 1000,
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

    # app = ProxyFix(app, x_for=1, x_host=1)

    return app
