from functools import wraps

from bson.objectid import ObjectId
from flask import current_app, request, make_response
import jwt
from jwt.exceptions import InvalidTokenError

from suprachat_backend.db import mongo


def token_required(f):
    @wraps(f)
    def decorator(*args, **kwargs):
        token = None

        if "x-access-tokens" in request.headers:
            token = request.headers["x-access-tokens"]

        if not token:
            return {"success": False, "error": "A valid token is needed."}

        try:
            data = jwt.decode(
                token, current_app.config["SECRET_KEY"], algorithms=("HS256",)
            )
            current_user = mongo.db.users.find_one(
                {"_id": ObjectId(data["user"]["_id"])}
            )
            if current_user is None:
                raise InvalidTokenError("Token is invalid, user does not exist.")
        except InvalidTokenError as e:
            print(e)
            return make_response(({"success": False, "error": "Invalid token"}, 401))

        return f(current_user, *args, **kwargs)

    return decorator
