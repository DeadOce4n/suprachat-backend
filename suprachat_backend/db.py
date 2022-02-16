import click
from flask.cli import with_appcontext
from flask_pymongo import PyMongo
from pymongo import TEXT

mongo = PyMongo()


def init_db():
    db = mongo.db
    collections = db.list_collection_names()

    for collection in collections:
        db.drop_collection(collection)

    db.create_collection("users")
    db.users.create_index([("nick", TEXT)], unique=True)


@click.command("init-db")
@with_appcontext
def init_db_command():
    init_db()
    click.echo("Initialized the database.")


def init_app(app):
    app.cli.add_command(init_db_command)
