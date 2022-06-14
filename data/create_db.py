import os
from pathlib import Path
import sqlite3


def create_db():
    db = (Path(__file__).parent / "tweet.db").resolve()
    scripts = (
        (Path(__file__).parent / "tweet_tables.sql").resolve(),
        (Path(__file__).parent / "tweet_indexes.sql").resolve(),
        (Path(__file__).parent / "tweet_views.sql").resolve(),
    )

    if not os.path.exists(db):
        print("Creating database {}".format(db))
        con = sqlite3.connect(db)
        for script in scripts:
            with open(script, "r") as f:
                con.executescript(f.read())
    else:
        print("Database {} already exists".format(db))


if __name__ == "__main__":
    create_db()
