import os
from flask import Blueprint, request, current_app, send_from_directory
from flask.helpers import make_response
from suprachat_backend.utils.files import allowed_filename
from suprachat_backend.utils.auth import token_required

bp = Blueprint("files", __name__)


@bp.get("/api/v1/users/<string:nick>/picture")
def download_file(nick):
    for file in os.listdir(current_app.config["UPLOAD_FOLDER"]):
        filename, _ = file.split(".")
        if filename == nick:
            return send_from_directory(current_app.config["UPLOAD_FOLDER"], file)
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], "default.png")


@bp.post("/api/v1/upload")
@token_required
def upload(current_user):
    if "file" not in request.files:
        return make_response(
            ({"success": False, "message": "File not present in request."}, 400)
        )
    file = request.files["file"]
    if file.filename == "":
        return make_response(
            ({"success": False, "message": "File not present in request."}, 400)
        )
    if file and allowed_filename(file.filename):
        for _file in os.listdir(current_app.config["UPLOAD_FOLDER"]):
            filename, _ = _file.split(".")
            if filename == current_user["nick"]:
                os.remove(os.path.join(current_app.config["UPLOAD_FOLDER"], _file))
        file.save(
            os.path.join(
                current_app.config["UPLOAD_FOLDER"],
                f"{current_user['nick']}.{file.filename.split('.')[1]}",
            )
        )
        return make_response(({"success": True, "message": "Upload successful."}, 200))
