import datetime as dt
import json

import jwt
from flask import Blueprint, current_app, make_response, request, jsonify
from webargs.flaskparser import use_args
from werkzeug.security import check_password_hash, generate_password_hash

from suprachat_backend.db import mongo
from suprachat_backend.models.user import UserSchema
from suprachat_backend.utils.auth import token_required
from suprachat_backend.utils.irc import IRCClient
from suprachat_backend.utils.passwd import (
    check_password_hash as check_password_hash_ergo,
)
from suprachat_backend.utils.validate_string import validate_string


def make_user_schema(request):
    fields = json.loads(request.data).keys()
    partial = request.method == "PATCH"
    return UserSchema(only=fields, partial=partial, context={"request": request})


bp = Blueprint("users", __name__)


@bp.get("/api/v1/users")
def get_all_users():
    users = mongo.db.users.find({})
    user_list = []
    for user in users:
        user_list.append(
            {
                "_id": str(user["_id"]),
                "nick": user["nick"],
                "email": user["email"],
                "registered_date": user["registered_date"],
                "password_from": user["password_from"] or None,
                "country": user["country"] or None,
                "about": user["about"] or None,
            }
        )
    return jsonify(user_list)


@bp.get("/api/v1/users/<string:nick>")
def get_user(nick):
    user = mongo.db.users.find_one({"nick": nick})
    if not user:
        return make_response(({"error": "Usuario no encontrado."}, 404))
    return {
        "_id": str(user["_id"]),
        "nick": user["nick"],
        "email": user["email"],
        "registered_date": user["registered_date"],
        "password_from": user["password_from"] or None,
        "country": user["country"] or None,
        "about": user["about"] or None,
    }


@bp.post("/api/v1/users/signup")
@use_args(make_user_schema)
def signup(args):
    nick = args.get("nick")
    email = args.get("email")
    password = args.get("password")
    password_hash = generate_password_hash(password)
    registered_date = dt.datetime.now().isoformat()
    verified = False

    # Checks if the user already exists in the MongoDB database or if the
    # email address is already in use; if it does, don't even bother checking
    # anything else
    existing_user = mongo.db.users.find_one({"$or": [{"nick": nick}, {"email": email}]})
    if existing_user:
        return make_response(({"error": "Nick o correo ya se encuentra en uso."}, 409))

    # Check if nick contains forbidden characters:  ,*?.!@:<>'\";#~&@%+-
    if not validate_string(nick):
        return make_response(
            (
                {
                    "error": "Nick contiene caracteres prohibidos, es muy corto"
                    " o muy largo.",
                },
                422,
            )
        )

    # Connect to the IRCd and attempt registration
    client = IRCClient(
        current_app.config["WEBIRCPASS"],
        request.remote_addr,
    )

    if client.connect():
        ircd_register_response = client.register(nick, email, password)
    else:
        return make_response(({"error": "Error de conexión al servidor IRC."}))

    if not ircd_register_response["success"]:
        return make_response(({"error": ircd_register_response["message"]}, 422))

    # If registration succeeeds, insert the newly created user into the database
    res = mongo.db.users.insert_one(
        {
            "nick": nick,
            "password": password_hash,
            "email": email,
            "registered_date": registered_date,
            "password_from": "supra",
            "verified": verified,
            "active": True,
            "country": None,
            "about": None,
        }
    )

    response = {
        "_id": str(res.inserted_id),
        "nick": nick,
        "email": email,
        "registered_date": registered_date,
        "verified": verified,
    }

    return make_response((response, 200))


@bp.post("/api/v1/users/verify")
def verify():
    body = json.loads(request.data)
    try:
        nick = body["nick"]
        code = body["code"]
    except KeyError:
        return make_response(({"error": "Se requiere un código de verificación."}, 400))
    # Connect to the IRCd and attempt registration
    client = IRCClient(
        current_app.config["WEBIRCPASS"],
        request.environ.get("HTTP_X_REAL_IP", request.remote_addr),
    )
    if client.connect():
        ircd_verify_response = client.verify(nick, code)
    else:
        return make_response(({"error": "Error de conexión al servidor IRC."}, 500))

    if not ircd_verify_response["success"]:
        return make_response(({"error": ircd_verify_response["message"]}, 400))

    mongo.db.users.update_one({"nick": nick}, {"$set": {"verified": True}})

    return make_response(({"verified": True}, 200))


@bp.get("/api/v1/users/login")
def login():
    auth = request.authorization

    if not auth or not auth.username or not auth.password:
        return make_response(({"error": "Hacen falta parámetros."}, 401))

    user = mongo.db.users.find_one({"nick": auth.username})

    if user is None:
        return make_response(({"error": "Usuario no encontrado."}, 404))

    # Users registered directly from the IRCd (through a client like WeeChat) have
    # their passwords hashed with a different algorithm, here we decide which
    # password hash checking function to use
    if user["password_from"] == "ergo":
        check_passwd_function = check_password_hash_ergo
    else:
        check_passwd_function = check_password_hash

    if check_passwd_function(user["password"], auth.password):
        token = jwt.encode(
            {
                "user": {
                    "_id": str(user["_id"]),
                    "nick": user["nick"],
                    "email": user["email"],
                    "registered_date": user["registered_date"] or None,
                    "verified": user["verified"],
                    "country": user["country"] or None,
                    "about": user["about"] or None,
                },
                "exp": dt.datetime.utcnow() + dt.timedelta(minutes=30),
            },
            current_app.config["SECRET_KEY"],
        )
        return {"token": token}
    else:
        return make_response(({"error": "Contraseña incorrecta"}, 401))


@bp.patch("/api/v1/users/<string:nick>")
@use_args(make_user_schema)
@token_required
def update_user(args, nick):
    country = args.get("country")
    about = args.get("about")

    existing_user = mongo.db.users.find_one({"nick": nick})

    if existing_user is None:
        return make_response(({"error": f"Usuario no encontrado."}, 404))

    fields_to_update = {}

    if country and (
        "country" not in existing_user.keys() or country != existing_user["country"]
    ):
        fields_to_update["country"] = country

    if about and (
        "about" not in existing_user.keys() or about != existing_user["about"]
    ):
        fields_to_update["about"] = about

    if len(fields_to_update.items()) == 0:
        return make_response(({"error": "Nada para modificar."}, 409))

    mongo.db.users.update_one({"nick": nick}, {"$set": {**fields_to_update}})

    response = {"nick": nick, **fields_to_update}

    return make_response((response, 200))
