from flask import Blueprint, request
from webargs.flaskparser import use_args

from suprachat_backend.controllers.user import (
    create,
    get_all,
    get_one,
    login,
    update,
    verify,
)
from suprachat_backend.models.user import make_user_schema
from suprachat_backend.utils.auth import token_required


bp = Blueprint("users", __name__)


@bp.get("/api/v1/users")
def users():
    return get_all()


@bp.get("/api/v1/users/<string:nick>")
def user(nick):
    return get_one(nick)


@bp.post("/api/v1/users/signup")
@use_args(make_user_schema)
def signup(args):
    return create(args, request)


@bp.post("/api/v1/users/verify")
def verify_user():
    return verify(request)


@bp.post("/api/v1/users/login")
def login_user():
    return login(request)


@bp.patch("/api/v1/users")
@use_args(make_user_schema)
@token_required
def update_user(current_user, args):
    return update(current_user, args)
