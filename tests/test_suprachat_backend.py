import datetime as dt
import os
import jwt
import sys

import pytest

from dotenv import load_dotenv
from suprachat_backend import create_app
from suprachat_backend.db import init_db, mongo
from suprachat_backend.utils.irc import IRCClient
from tests.utils.init_ergo import Ircd
import base64

try:
    load_dotenv()
    ergo_path = os.environ["ERGO_PATH"]
except KeyError:
    print("Please specify ERGO_PATH in your environment variables.")
    sys.exit(1)


@pytest.fixture
def app():
    app = create_app()
    app.config.update({"TESTING": True, "MONGO_URI": "mongodb://localhost:27017/test"})

    with app.app_context():
        init_db()

    yield app

    collections = mongo.db.list_collection_names()

    for collection in collections:
        mongo.db.drop_collection(collection)


@pytest.fixture
def client(app):
    return app.test_client()


def test_empty_db(client):
    """Start with a blank database."""

    response = client.get("/api/v1/users")
    json_data = response.get_json()
    assert len(json_data) == 0


def test_nonexistent_user(client):
    """Try to fetch a non-existent user."""

    response = client.get("/api/v1/users/DeadOcean")

    assert "404" in response.status


def test_register_user(client):
    """Register a new user."""

    test_user = {
        "nick": "DeadOcean",
        "email": "admin@suprachat.net",
        "password": "password",
    }

    with Ircd(ergo_path):
        response = client.post(
            "/api/v1/users/signup",
            json=test_user,
        )

    assert response.status == "200 OK"


def test_get_user(client):
    """Get a user from the database."""

    test_user = {
        "nick": "DeadOcean",
        "email": "admin@suprachat.net",
        "password": "password",
        "password_from": "ergo",
        "registered_date": dt.datetime.now().isoformat(),
        "verified": True,
        "country": "México",
        "about": "i'm a random user",
    }

    mongo.db.users.insert_one({**test_user})

    response = client.get(f"/api/v1/users/{test_user['nick']}")

    assert "200" in response.status
    assert response.json["nick"] == test_user["nick"]
    assert response.json["email"] == test_user["email"]
    assert response.json["password_from"] == "ergo" or "supra"


def test_register_existing_user(client):
    """Try to register a user with an nick that's already in use."""

    test_user = {
        "nick": "DeadOcean",
        "email": "admin@suprachat.net",
        "password": "password",
    }

    mongo.db.users.insert_one({**test_user})

    response = client.post(
        "/api/v1/users/signup",
        json=test_user,
    )

    assert "409" in response.status


def test_login_existing_user(app):
    """Log into an existing account."""
    test_user = {
        "nick": "DeadOcean",
        "email": "admin@suprachat.net",
        "password": "password",
    }

    client = app.test_client()

    auth = base64.b64encode(
        f"{test_user['nick']}:{test_user['password']}".encode("utf-8")
    )

    with Ircd(ergo_path):
        _ = client.post("/api/v1/users/signup", json={**test_user})
        response = client.get(
            "/api/v1/users/login",
            headers={"Authorization": f"Basic {auth.decode('utf-8')}"},
        )
        token = response.json["token"]
        decoded_token = jwt.decode(
            token,
            app.config["SECRET_KEY"],
            algorithms=[
                "HS256",
            ],
        )

    assert decoded_token["user"]["nick"] == test_user["nick"]
    assert decoded_token["user"]["email"] == test_user["email"]
    assert decoded_token["user"]["nick"] == test_user["nick"]


def test_verification(client, mocker):
    mocker.patch.object(IRCClient, "connect", return_value=True)
    mocker.patch.object(IRCClient, "verify", return_value={"success": True})

    with Ircd(ergo_path):
        response = client.post(
            "/api/v1/users/verify", json={"nick": "DeadOcean", "code": "somecode"}
        )

    assert "200" in response.status
    assert response.json["verified"] == True


def test_update_user_ok(app):
    test_user = {
        "nick": "DeadOcean",
        "email": "admin@suprachat.net",
        "password": "password",
        "about": "lorem ipsum dolor sit amet",
        "country": "Andorra",
    }

    auth = base64.b64encode(
        f"{test_user['nick']}:{test_user['password']}".encode("utf-8")
    )

    client = app.test_client()

    with Ircd(ergo_path):
        _ = client.post(
            "/api/v1/users/signup",
            json={
                "nick": test_user["nick"],
                "email": test_user["email"],
                "password": test_user["password"],
            },
        )

    response = client.get(
        "/api/v1/users/login",
        headers={"Authorization": f"Basic {auth.decode('utf-8')}"},
    )

    token = response.json["token"]

    response = client.patch(
        f"/api/v1/users",
        headers={"X-Access-Tokens": token},
        json={
            "password": "anotherPassword",
            "country": test_user["country"],
            "about": test_user["about"],
        },
    )

    assert "200" in response.status
    assert response.json["nick"] == test_user["nick"]
    assert response.json["about"] is not None
    assert response.json["country"] is not None
    assert response.json["password"] is not None
