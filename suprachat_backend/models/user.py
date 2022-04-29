import json

from marshmallow import Schema, fields, validate


class UserSchema(Schema):
    nick = fields.Str(validate=validate.Length(min=3), required=True)
    email = fields.Email(required=True)
    password = fields.Str(validate=validate.Length(min=8), required=True)
    country = fields.Str(required=False)
    about = fields.Str(validate=validate.Length(max=300), required=False)


def make_user_schema(request):
    fields = json.loads(request.data).keys()
    partial = request.method == "PATCH"
    return UserSchema(only=fields, partial=partial, context={"request": request})
