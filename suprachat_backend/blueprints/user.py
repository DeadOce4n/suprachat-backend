from flask import Blueprint, current_app, request
from webargs import fields
from webargs.flaskparser import use_args

from suprachat_backend.controllers.user import (
    get,
    find,
    update_self,
    update,
    register,
    login,
    verify,
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
def find_users(args):
    return find(args)


@bp.get("/api/v1/users/<string:nick>")
def get_user(nick):
    return get(nick)


@bp.patch("/api/v1/users")
@use_args(make_user_schema)
@token_required
def update_me(current_user, args):
    return update_self(current_user, args)


@bp.put("/api/v1/users/<string:_id>")
@use_args({
    "password": fields.Str(required=False),
    "verified": fields.Bool(required=False),
    "country": fields.Str(required=False),
    "about": fields.Str(required=False),
})
@token_required
def update_one(current_user, args, _id):
    return update(current_user, args, _id)


@bp.post("/api/v1/users/signup")
@use_args(make_user_schema)
def register_user(args):
    return register(args, request)


@bp.post("/api/v1/users/verify")
def verify_user():
    return verify(request)


@bp.post("/api/v1/users/login")
def login_user():
    return login(request)
