ALLOWED_FILETYPES = {"png", "jpg", "jpeg", "gif", "webp"}


def allowed_filename(filename: str):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_FILETYPES
