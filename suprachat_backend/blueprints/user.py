from flask import Blueprint, request
from webargs import fields
from webargs.flaskparser import use_args

from suprachat_backend.controllers.user import (
    find as _find,
    find_one as _find_one,
    update_me as _update_me,
    update as _update,
    register as _register,
    login as _login,
    verify as _verify,
)
from suprachat_backend.models.user import make_user_schema
from suprachat_backend.utils.auth import token_required


bp = Blueprint("users", __name__)


@bp.get("/api/v1/users")
@use_args(
    {
        "filter": fields.Str(required=True),
        "page": fields.Int(required=True),
        "limit": fields.Int(required=True),
    },
    location="query",
)
def find(args):
    return _find(args)


@bp.get("/api/v1/users/<string:nick>")
def find_one(nick):
    return _find_one(nick)


@bp.patch("/api/v1/users")
@use_args(make_user_schema)
@token_required
def update_me(current_user, args):
    return _update_me(current_user, args)


@bp.put("/api/v1/users/<string:_id>")
@use_args(
    {
        "password": fields.Str(required=False),
        "verified": fields.Bool(required=False),
        "country": fields.Str(required=False),
        "about": fields.Str(required=False),
    }
)
@token_required
def update(current_user, args, _id):
    return _update(current_user, args, _id)


@bp.post("/api/v1/users/signup")
@use_args(make_user_schema)
def register(args):
    return _register(args, request)


@bp.post("/api/v1/users/verify")
def verify():
    return _verify(request)


@bp.post("/api/v1/users/login")
def login():
    return _login(request)
