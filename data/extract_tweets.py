import os
from pathlib import Path
import logging
from time import sleep
import tweepy
import requests
import sqlite3
from create_db import create_db

EXPANSIONS = ["referenced_tweets.id", "referenced_tweets.id.author_id"]
TWEET_FIELDS = [
    "referenced_tweets",
    "in_reply_to_user_id",
    "author_id",
    "lang",
    "entities",
    "created_at",
]

# Extracts Tweets for the IDs that exist in the dataset files
def extract_tweets_file(con: sqlite3.Connection, client: tweepy.Client):

    # Get already processed file names
    log = (Path(__file__).parent / "processed_file_log.txt").resolve()
    if os.path.isfile(log):
        with open(log, "r") as f:
            processed_files = set(line.strip() for line in f.readlines())
    else:
        processed_files = set()

    # Process every file sequentially in reverse order (latest first so there is more probability of getting previous tweets included in the responses)
    dataset_root = (Path(__file__).parent / "russo_ukraine_dataset").resolve()
    for dir in reversed(os.listdir(dataset_root)):
        print("Processing directory '{}'".format(dir))
        for file in reversed(os.listdir(dataset_root / dir)):
            if file not in processed_files:
                print("\tProcessing file '{}'".format(file))

                with open(dataset_root / dir / file, "r") as f:
                    file_ids = [line.strip() for line in f.readlines()]

                batchNo = 0
                batch_ids = []
                processed_count = 0
                for index, id in enumerate(reversed(file_ids)):
                    # Filter out Tweets that already exist in the database and are either complete or unavailable (not partial).
                    if not con.execute(
                        "SELECT 1 FROM Tweet WHERE TweetId = ? AND TweetTypeCode IN (?, ?)",
                        [id, "U", "C"],
                    ).fetchone():
                        batch_ids.append(id)
                    # Process IDs in batches of at most 100, which is the API's limit.
                    if len(batch_ids) == 100 or (
                        len(batch_ids) != 0 and index == len(file_ids) - 1
                    ):
                        print(
                            "\t\tBatch No {}, {} IDs ({} - {})".format(
                                batchNo, len(batch_ids), batch_ids[0], batch_ids[-1]
                            )
                        )
                        # Process the batch as a single transaction.
                        with con:
                            process_batch_request(con, client, batch_ids)
                        processed_count += len(batch_ids)
                        batchNo += 1
                        batch_ids.clear()
                print(
                    "\tProcessed {} Tweet IDs. {} out of {} were already processed.\n".format(
                        processed_count, len(file_ids) - processed_count, len(file_ids)
                    )
                )

                # Record processed file name
                processed_files.add(file)
                with open(log, "a") as f:
                    f.write(file + "\n")
            else:
                print("\tFile '{}' already processed".format(file))
    con.close()


# Extracts Tweets for the IDs of partial Tweets that exist in the database
def extract_tweets_partial(con: sqlite3.Connection, client: tweepy.Client):

    initial_count = con.execute("SELECT COUNT(*) FROM Tweet_Partial").fetchone()[0]
    print("Processing partial Tweets ({} IDs total)".format(initial_count))

    batchNo = 0
    processed_count = 0
    # Query and process partial Tweets in batches of at most 100. The process will repeat until there are no partial Tweets remaining.
    while True:
        batch_ids = [
            row[0]
            for row in con.execute(
                "SELECT TweetId FROM Tweet_Partial LIMIT 100"
            ).fetchall()
        ]
        if batch_ids:
            print("\tBatch No {}, {} IDs".format(batchNo, len(batch_ids)))
            with con:
                process_batch_request(con, client, batch_ids)
            batchNo += 1
            processed_count += len(batch_ids)
        else:
            print(
                "Partial Tweet processing complete ({} IDs processed, with an initial count of {})".format(
                    processed_count, initial_count
                )
            )
            break


# Attempts an extraction of Tweets for the IDs that was previously recorded as unavailable
def extract_tweets_unavailable(con: sqlite3.Connection, client: tweepy.Client):

    # Query all unavailable Tweets IDs and process each ID (at most) once, since it may still be unavailable.
    unavailable_ids = [
        row[0]
        for row in con.execute("SELECT TweetId FROM Tweet_Unavailable").fetchall()
    ]
    print(
        "Processing previously unavailable Tweets ({} IDs total)".format(
            len(unavailable_ids)
        )
    )

    batchNo = 0
    batch_ids = []
    processed_count = 0
    for index, id in enumerate(unavailable_ids):
        # Filter out Tweets that already exist in the database and are either complete or parial.
        if not con.execute(
            "SELECT 1 FROM Tweet WHERE TweetId = ? AND TweetTypeCode IN (?, ?)",
            [id, "C", "P"],
        ).fetchone():
            batch_ids.append(id)
        # Process IDs in batches of at most 100, which is the API's limit.
        if len(batch_ids) == 100 or (
            len(batch_ids) != 0 and index == len(unavailable_ids) - 1
        ):
            print("\tBatch No {}, {} IDs".format(batchNo, len(batch_ids)))
            # Process the batch as a single transaction.
            with con:
                process_batch_request(con, client, batch_ids)
            processed_count += len(batch_ids)
            batchNo += 1
            batch_ids.clear()
    print(
        "Unavailable Tweet processing complete ({} IDs processed, with an initial count of {})".format(
            processed_count, len(unavailable_ids)
        )
    )


def process_batch_request(con: sqlite3.Connection, client: tweepy.Client, ids):

    if len(ids) > 100:
        print(
            "Batch request size limit exceeded ({} IDs > 100). Aborting".format(
                len(ids)
            )
        )
        exit()

    retry_count = 1
    while True:
        try:
            response = client.get_tweets(
                ids, expansions=EXPANSIONS, tweet_fields=TWEET_FIELDS
            )
            break
        except (tweepy.TwitterServerError, requests.exceptions.ConnectionError) as e:
            print("\t\t\tError: {}".format(e))
            sleep_time = 10 * retry_count
            print("\t\t\tRetrying in {} seconds.".format(sleep_time))
            sleep(sleep_time)
            retry_count += 1
            print("\t\t\tRetry {}".format(retry_count))

    if response.includes:
        # Add users included in the response ( authors, RT's initial authors, users replied to )
        for user in response.includes.get("users", []):
            con.execute(
                "INSERT OR IGNORE INTO Account (AccountId, Username) VALUES (?, ?)",
                [user.id, user.username],
            )

        # For referenced tweets included in the response, add a Tweet_Partial for any tweet they in turn refer to (quotes, replies to)
        # These Tweet_Partial 's will be queried at a later time
        for tweet in response.includes.get("tweets", []):
            if tweet.referenced_tweets:
                for ref_tweet in tweet.referenced_tweets:
                    add_tweet_partial(con, ref_tweet.id)

        # Now that any possible parent tweets are added, add a Tweet_Complete for any referenced tweet included in the response (retweeted tweets, quoted tweets, tweets replied to)
        for tweet in response.includes.get("tweets", []):
            add_tweet_complete(con, tweet)

    # Add a Tweet_Unavailable for any tweets that get errors (not found, unauthorized)
    if response.errors:
        for error in response.errors:
            if (
                error["resource_type"]
                and error["resource_type"] == "tweet"
                and error["resource_id"]
            ):
                add_tweet_unavailable(con, error["resource_id"])

    # Finally, add a Tweet_Complete for any tweet in the response data (the ones for the requested IDs)
    if response.data:
        for tweet in response.data:
            add_tweet_complete(con, tweet)


def add_tweet_partial(con: sqlite3.Connection, tweet_id):
    if not con.execute("SELECT 1 FROM Tweet WHERE TweetId = ?", [tweet_id]).fetchone():
        con.execute(
            "INSERT INTO Tweet (TweetId, TweetTypeCode) VALUES (?, ?)", [tweet_id, "P"]
        )
        con.execute("INSERT INTO Tweet_Partial (TweetId) VALUES (?)", [tweet_id])


def add_tweet_unavailable(con: sqlite3.Connection, tweet_id):
    if con.execute(
        "SELECT 1 FROM Tweet WHERE TweetId = ? AND TweetTypeCode != 'P'", [tweet_id]
    ).fetchone():
        return
    elif con.execute(
        "SELECT 1 FROM Tweet_Partial WHERE TweetId = ?", [tweet_id]
    ).fetchone():
        con.execute("DELETE FROM Tweet_Partial WHERE TweetId = ?", [tweet_id])
        con.execute(
            "UPDATE Tweet SET TweetTypeCode = ? WHERE TweetId = ?", ["U", tweet_id]
        )
    else:
        con.execute(
            "INSERT INTO Tweet (TweetId, TweetTypeCode) VALUES (?, ?)", [tweet_id, "U"]
        )
    con.execute("INSERT INTO Tweet_Unavailable (TweetId) VALUES (?)", [tweet_id])


def add_tweet_complete(con: sqlite3.Connection, tweet: tweepy.Tweet):
    if con.execute(
        "SELECT 1 FROM Tweet_Complete WHERE TweetId = ?", [tweet.id]
    ).fetchone():
        return
    elif con.execute(
        "SELECT 1 FROM Tweet_Partial WHERE TweetId = ?", [tweet.id]
    ).fetchone():
        con.execute("DELETE FROM Tweet_Partial WHERE TweetId = ?", [tweet.id])
        con.execute(
            "UPDATE Tweet SET TweetTypeCode = ? WHERE TweetId = ?", ["C", tweet.id]
        )
    elif con.execute(
        "SELECT 1 FROM Tweet_Unavailable WHERE TweetId = ?", [tweet.id]
    ).fetchone():
        con.execute("DELETE FROM Tweet_Unavailable WHERE TweetId = ?", [tweet.id])
        con.execute(
            "UPDATE Tweet SET TweetTypeCode = ? WHERE TweetId = ?", ["C", tweet.id]
        )
    else:
        con.execute(
            "INSERT INTO Tweet (TweetId, TweetTypeCode) VALUES (?, ?)", [tweet.id, "C"]
        )

    # If Tweet is a Retweet, add a Tweet_Retweet and return
    if tweet.referenced_tweets:
        ref_tweet = next(
            (
                ref_tweet
                for ref_tweet in tweet.referenced_tweets
                if ref_tweet.type == "retweeted"
            ),
            False,
        )
        if ref_tweet:
            con.execute(
                "INSERT INTO Tweet_Complete (TweetId, AuthorId, TweetDtm, IsRetweet) VALUES (?, ?, ?, ?)",
                [tweet.id, tweet.author_id, tweet.created_at, True],
            )
            con.execute(
                "INSERT INTO Tweet_Retweet (RetweetId, ReferenceTweetId) VALUES (?, ?)",
                [tweet.id, ref_tweet.id],
            )
            return

    # Else add a Tweet_Text and process Tweet fully
    con.execute(
        "INSERT INTO Tweet_Complete (TweetId, AuthorId, TweetDtm, IsRetweet) VALUES (?, ?, ?, ?)",
        [tweet.id, tweet.author_id, tweet.created_at, False],
    )
    con.execute(
        "INSERT INTO Tweet_Text (TweetId, Tweet, Lang) VALUES (?, ?, ?)",
        [tweet.id, tweet.text, tweet.lang],
    )

    # Process Tweet if it is a reply or quote
    if tweet.referenced_tweets:
        for ref_tweet in tweet.referenced_tweets:
            if ref_tweet.type == "quoted":
                con.execute(
                    "INSERT INTO TweetReference (TweetId, ReferenceTypeCode, ReferenceTweetId) VALUES (?, ?, ?)",
                    [tweet.id, "Qu", ref_tweet.id],
                )
            elif ref_tweet.type == "replied_to":
                con.execute(
                    "INSERT INTO TweetReference (TweetId, ReferenceTypeCode, ReferenceTweetId) VALUES (?, ?, ?)",
                    [tweet.id, "Re", ref_tweet.id],
                )

    # Process Tweet Entities
    if tweet.entities:
        for mention in tweet.entities.get("mentions", []):
            con.execute(
                "INSERT OR IGNORE INTO Account (AccountId, Username) VALUES (?, ?)",
                [mention["id"], mention["username"]],
            )
            entity_no = con.execute(
                "SELECT COALESCE(MAX(EntityNo) + 1, 1) FROM Entity WHERE TweetId = ?",
                [tweet.id],
            ).fetchone()[0]
            con.execute(
                "INSERT INTO Entity (TweetId, EntityNo, EntityTypeCode, OffsetStart, OffsetEnd) VALUES (?, ?, ?, ?, ?)",
                [tweet.id, entity_no, "Me", mention["start"], mention["end"]],
            )
            con.execute(
                "INSERT INTO Entity_Mention (TweetId, EntityNo, MentionAccountId) VALUES (?, ?, ?)",
                [tweet.id, entity_no, mention["id"]],
            )
        for hashtag in tweet.entities.get("hashtags", []):
            con.execute(
                "INSERT OR IGNORE INTO Hashtag (Hashtag) VALUES (?)", [hashtag["tag"]]
            )
            entity_no = con.execute(
                "SELECT COALESCE(MAX(EntityNo) + 1, 1) FROM Entity WHERE TweetId = ?",
                [tweet.id],
            ).fetchone()[0]
            con.execute(
                "INSERT INTO Entity (TweetId, EntityNo, EntityTypeCode, OffsetStart, OffsetEnd) VALUES (?, ?, ?, ?, ?)",
                [tweet.id, entity_no, "Ha", hashtag["start"], hashtag["end"]],
            )
            con.execute(
                "INSERT INTO Entity_Hashtag (TweetId, EntityNo, Hashtag) VALUES (?, ?, ?)",
                [tweet.id, entity_no, hashtag["tag"]],
            )
        for annotation in tweet.entities.get("annotations", []):
            if annotation["type"] == "Person":
                annotationTypeCode = "Pe"
            elif annotation["type"] == "Place":
                annotationTypeCode = "Pl"
            elif annotation["type"] == "Product":
                annotationTypeCode = "Pr"
            elif annotation["type"] == "Organization":
                annotationTypeCode = "Or"
            elif annotation["type"] == "Other":
                annotationTypeCode = "O"
            con.execute(
                "INSERT OR IGNORE INTO Annotation (AnnotationTypeCode, Annotation) VALUES (?, ?)",
                [annotationTypeCode, annotation["normalized_text"]],
            )
            entity_no = con.execute(
                "SELECT COALESCE(MAX(EntityNo) + 1, 1) FROM Entity WHERE TweetId = ?",
                [tweet.id],
            ).fetchone()[0]
            con.execute(
                "INSERT INTO Entity (TweetId, EntityNo, EntityTypeCode, OffsetStart, OffsetEnd) VALUES (?, ?, ?, ?, ?)",
                [tweet.id, entity_no, "An", annotation["start"], annotation["end"]],
            )
            con.execute(
                "INSERT INTO Entity_Annotation (TweetId, EntityNo, AnnotationTypeCode, Annotation) VALUES (?, ?, ?, ?)",
                [
                    tweet.id,
                    entity_no,
                    annotationTypeCode,
                    annotation["normalized_text"],
                ],
            )
        for url in tweet.entities.get("urls", []):
            entity_no = con.execute(
                "SELECT COALESCE(MAX(EntityNo) + 1, 1) FROM Entity WHERE TweetId = ?",
                [tweet.id],
            ).fetchone()[0]
            con.execute(
                "INSERT INTO Entity (TweetId, EntityNo, EntityTypeCode, OffsetStart, OffsetEnd) VALUES (?, ?, ?, ?, ?)",
                [tweet.id, entity_no, "Ur", url["start"], url["end"]],
            )
            con.execute(
                "INSERT INTO Entity_Url (TweetId, EntityNo, Url) VALUES (?, ?, ?)",
                [tweet.id, entity_no, url["url"]],
            )


if __name__ == "__main__":
    logger = logging.getLogger("tweepy")
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    logger.addHandler(handler)

    # Create tweet.db SQLite database if it does not exist and get a connection
    db = (Path(__file__).parent / "tweet.db").resolve()
    if not os.path.exists(db):
        create_db()
    con = sqlite3.connect(db)

    # Create Twitter API client with bearer token authentication
    bearer_token = os.environ.get("TWITTER_BEARER_TOKEN")
    if not bearer_token:
        print("TWITTER_BEARER_TOKEN environment variable not found. Aborting!")
        exit()
    client = tweepy.Client(bearer_token=bearer_token, wait_on_rate_limit=True)

    mode = 0
    print(
        "\n[1] Extract File IDs\n[2] Extract Partial Tweets IDs\n[3] Extract Unavailable Tweet IDs\n"
    )
    while mode not in (1, 2, 3):
        try:
            mode = int(input("Choose extraction source (1-3): "))
        except ValueError:
            continue
    if mode == 1:
        extract_tweets_file(con, client)
    elif mode == 2:
        extract_tweets_partial(con, client)
    elif mode == 3:
        extract_tweets_unavailable(con, client)
