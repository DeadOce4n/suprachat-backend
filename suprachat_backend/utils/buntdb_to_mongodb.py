from datetime import datetime
import json
from json.decoder import JSONDecodeError
import sys

import click
from flask import current_app
from flask.cli import with_appcontext
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError


def find_users(file: str) -> list[dict]:
    """
    Finds users registered on a BuntDB database file generated by ergo IRCd and
    register them into a MongoDB database.

    Args:
        file: The BuntDB file to look into.

    Returns:
        A list containing a dictionary of every user found and their data. For
        example:

            {"nick": "DeadOcean",
             "password_hash": "someAwesomePasswordHash",
             "registered_date": '2021-05-08T20:01:43'}
    """
    try:
        with open(file) as f:
            lines = list(map(lambda line: line.strip(), reversed(f.readlines())))
            users: list[dict] = []

            for index, line in enumerate(lines):
                if line.startswith("account.name"):
                    user = {"nick": lines[index - 2]}
                    if user not in users and not user["nick"].startswith("$"):
                        print(f"Found nick: {user['nick']}")
                        users.append(user)

            for index, line in enumerate(lines):
                if line.startswith("account.credentials"):
                    nick = line.split(" ")[1]
                    for user in users:
                        if (
                            nick == user["nick"].lower()
                            and "password_hash" not in user.keys()
                        ):
                            try:
                                password_hash = json.loads(lines[index - 2])[
                                    "PassphraseHash"
                                ]
                                user["password_hash"] = password_hash
                            except JSONDecodeError:
                                pass

            for index, line in enumerate(lines):
                if line.startswith("account.registered.time"):
                    nick = line.split(" ")[1]
                    for user in users:
                        if (
                            nick == user["nick"].lower()
                            and "registered_date" not in user.keys()
                        ):
                            try:
                                timestamp = float(lines[index - 2].strip()[0:10])
                                user["registered_date"] = datetime.fromtimestamp(
                                    timestamp
                                ).isoformat()
                            except ValueError:
                                pass

    except FileNotFoundError:
        print("Please copy your ircd.db file to this same directory.")
        sys.exit(1)

    return users


def insert_into_mongo():
    db = MongoClient(current_app.config["MONGO_URI"])
    users = db.suprachat.users
    found_users = find_users("./ircd.db")
    inserted_users = 0

    for user in found_users:
        try:
            users.insert_one(
                {
                    "nick": user["nick"],
                    "password": user["password_hash"],
                    "email": None,
                    "registered_date": user["registered_date"],
                    "password_from": "ergo",
                    "verified": True,
                    "active": True,
                    "country": None,
                    "about": None,
                }
            )
            inserted_users += 1
        except DuplicateKeyError:
            print(f"User {user['nick']} already exists in database, skipping...")

    print(f"Inserted {inserted_users} users into the database.")


@click.command("bunt-to-mongo")
@with_appcontext
def insert_command():
    insert_into_mongo()


def init_app(app):
    app.cli.add_command(insert_command)
