from flask import Blueprint, request

from suprachat_backend.controllers.files import download, upload
from suprachat_backend.utils.auth import token_required

bp = Blueprint("files", __name__)


@bp.get("/api/v1/upload/<path:name>")
def download_file(name):
    return download(name)


@bp.post("/api/v1/upload")
@token_required
def upload_file(current_user):
    return upload(current_user, request)
