import datetime as dt
import json

from flask import current_app, jsonify, make_response
import jwt
from werkzeug.security import check_password_hash, generate_password_hash

from suprachat_backend.db import mongo
from suprachat_backend.utils.irc import IRCClient
from suprachat_backend.utils.passwd import (
    check_password_hash as check_password_hash_ergo,
)
from suprachat_backend.utils.validate_string import validate_string


def get_all():
    users = mongo.db.users.find({})
    user_list = []
    for user in users:
        user_list.append(
            {
                "_id": str(user["_id"]),
                "nick": user["nick"],
                "email": user["email"],
                "registered_date": user["registered_date"],
                "password_from": user.get("password_from", None),
                "country": user.get("country", None),
                "about": user.get("about", None),
                "picture": user.get("picture", None),
            }
        )
    return jsonify(user_list)


def get_one(nick):
    user = mongo.db.users.find_one({"nick": nick})
    if not user:
        return make_response(({"error": "Usuario no encontrado."}, 404))
    return {
        "_id": str(user["_id"]),
        "nick": user["nick"],
        "email": user["email"],
        "registered_date": user.get("registered_date", None),
        "password_from": user.get("password_from", None),
        "country": user.get("country", None),
        "about": user.get("about", None),
        "picture": user.get("picture", None),
    }


def create(args, request):
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
        current_app.logger.info(f"Ya existe un usuario con ese nick o correo: {nick}, {email}")
        return make_response(({"error": "Nick o correo ya se encuentra en uso."}, 409))

    # Check if nick contains forbidden characters:  ,*?.!@:<>'\";#~&@%+-
    if not validate_string(nick):
        current_app.logger.info("Contraseña contiene caracteres prohibidos")
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
        current_app.logger.info("Error al conectarse al servidor IRC")
        return make_response(({"error": "Error de conexión al servidor IRC."}))

    if not ircd_register_response["success"]:
        current_app.logger.info(f"Falló el registro: {ircd_register_response['message']}")
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
            "picture": None,
        }
    )

    response = {
        "_id": str(res.inserted_id),
        "nick": nick,
        "email": email,
        "registered_date": registered_date,
        "verified": verified,
    }
    current_app.logger.info("Usuario registrado exitosamente!")
    return make_response((response, 200))


def verify(request):
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
        current_app.logger.info("Error al conectarse al servidor IRC")
        return make_response(({"error": "Error de conexión al servidor IRC."}, 500))

    if not ircd_verify_response["success"]:
        current_app.logger.info("Error al verificar el registro")
        return make_response(({"error": ircd_verify_response["message"]}, 400))

    mongo.db.users.update_one({"nick": nick}, {"$set": {"verified": True}})

    current_app.logger.info("Verificación exitosa!")
    return make_response(({"verified": True}, 200))


def login(request):
    auth = request.authorization

    if not auth or not auth.username or not auth.password:
        return make_response(({"error": "Hacen falta parámetros."}, 401))

    user = mongo.db.users.find_one({"nick": auth.username})

    if user is None:
        return make_response(({"error": "Usuario no encontrado."}, 404))

    # Users registered directly from the IRCd (through a client like WeeChat) have
    # their passwords hashed with a different algorithm, here we decide which
    # password hash checking function to use
    new_passwd_hash = None

    if user["password_from"] == "ergo":
        current_app.logger.info("Cuenta creada directamente en el IRCd, se migrará contraseña")
        check_passwd_function = check_password_hash_ergo
        new_passwd_hash = generate_password_hash(auth.password)
    else:
        check_passwd_function = check_password_hash

    if check_passwd_function(user["password"], auth.password):
        if new_passwd_hash is not None:
            mongo.db.users.update_one(
                {"nick": auth.username},
                {"$set": {"password": new_passwd_hash, "password_from": "supra"}},
            )
        token = jwt.encode(
            {
                "user": {
                    "_id": str(user["_id"]),
                    "nick": user["nick"],
                    "email": user["email"],
                    "registered_date": user.get("registered_date", None),
                    "verified": user.get("verified", None),
                    "country": user.get("country", None),
                    "about": user.get("about", None),
                    "picture": user.get("picture", None),
                },
                "exp": dt.datetime.utcnow() + dt.timedelta(minutes=30),
            },
            current_app.config["SECRET_KEY"],
        )
        current_app.logger.info(f"Usuario {user['nick']} inicia sesión")
        return {"token": token}
    else:
        current_app.logger.info(f"Inicio de sesión fallido por {user['nick']}")
        return make_response(({"error": "Contraseña incorrecta"}, 401))


def update(current_user, args):
    country = args.get("country")
    about = args.get("about")
    password = args.get("password")

    existing_user = mongo.db.users.find_one({"nick": current_user["nick"]})

    if existing_user is None:
        return make_response(({"error": f"Usuario no encontrado."}, 404))

    fields_to_update = {}

    if country and (
        "country" not in existing_user.keys() or country != existing_user["country"]
    ):
        fields_to_update["country"] = country

    if about is not None and (
        "about" not in existing_user.keys() or about != existing_user["about"]
    ):
        fields_to_update["about"] = about

    if password:
        stored_pw_hash = existing_user["password"]
        if not check_password_hash(stored_pw_hash, password):
            fields_to_update["password"] = generate_password_hash(password)

    if len(fields_to_update.items()) == 0:
        return make_response(({"error": "Nada para modificar."}, 409))

    mongo.db.users.update_one(
        {"nick": current_user["nick"]}, {"$set": {**fields_to_update}}
    )

    response = {"nick": current_user["nick"], **fields_to_update}

    return make_response((response, 200))
