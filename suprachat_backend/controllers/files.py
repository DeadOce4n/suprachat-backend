import os
from uuid import uuid4

from flask import current_app, make_response, send_from_directory

from suprachat_backend.db import mongo
from suprachat_backend.utils.files import allowed_filename


def download(name):
    file = name if name != "null" else "default.png"
    current_app.logger.info(f"Descargando archivo: {file}")
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], file)


def upload(current_user, request):
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
        filename = f"{uuid4().hex}.{file.filename.split('.')[-1]}"
        file.save(os.path.join(current_app.config["UPLOAD_FOLDER"], filename))
        mongo.db.users.update_one(
            {"nick": current_user["nick"]}, {"$set": {"picture": filename}}
        )
        current_app.logger.info(f"Se guardó la imagen {file.filename} como {filename}")
        return make_response(({"message": "Upload successful.", "path": filename}, 200))
