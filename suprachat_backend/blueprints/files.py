import os
from uuid import uuid4

from flask import Blueprint, current_app, request, send_from_directory
from flask.helpers import make_response

from suprachat_backend.db import mongo
from suprachat_backend.utils.auth import token_required
from suprachat_backend.utils.files import allowed_filename

bp = Blueprint("files", __name__)


@bp.get("/api/v1/upload/<path:name>")
def download_file(name):
    if name == "null":
        return send_from_directory(current_app.config["UPLOAD_FOLDER"], "default.png")
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], name)


@bp.post("/api/v1/upload")
@token_required
def upload(current_user):
    if "file" not in request.files:
        return make_response(
            ({"success": False, "message": "File not present in request."}, 400)
        )
    file = request.files["file"]
    if not file.filename:
        return make_response(
            ({"success": False, "message": "File not present in request."}, 400)
        )
    if file and allowed_filename(file.filename):
        filename = f"{uuid4().hex}.{file.filename.split('.')[1]}"
        file.save(os.path.join(current_app.config["UPLOAD_FOLDER"], filename))
        user = mongo.db.users.update_one(
            {"nick": current_user["nick"]}, {"$set": {"picture": filename}}
        )
        return make_response(({"message": "Upload successful.", "path": filename}, 200))
