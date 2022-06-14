import logging
import os
from pathlib import Path
import sqlite3
import networkx as nx
from tqdm import tqdm

logging.basicConfig(
    format="%(asctime)s : %(levelname)s : %(message)s", level=logging.INFO
)

db = (Path(__file__).parent / "../data/tweet.db").resolve()
con = sqlite3.connect(db)

edge_query = """
    SELECT A, B
    FROM {}
    WHERE A IN 
    (
        SELECT AuthorId FROM TweetCountSummary WHERE Lang='en' AND Count >= ?
    )
    AND B IN 
    (
        SELECT AuthorId FROM TweetCountSummary WHERE Lang='en' AND Count >= ?
    )
"""

edge_types = (
    ("retweet", "EdgeRetweet_V"),
    ("quote", "EdgeQuote_V"),
    ("reply", "EdgeReply_V"),
    ("mention", "EdgeMention_V"),
)


ego_usernames = ["RT_com", "KyivPost", "SputnikInt", "KyivIndependent", "MoscowTimes"]
ego_nodes = con.execute(
    f"SELECT AccountId, Username FROM Account WHERE Username IN ({','.join('?' * len(ego_usernames))})",
    ego_usernames,
).fetchall()

min_tweet_count = None
while not min_tweet_count or min_tweet_count < 1:
    try:
        min_tweet_count = int(input("Minimum tweet count: "))
    except ValueError:
        continue

# Extract a network as an edgelist, for every type of user interaction
for name, view in edge_types:
    edgelist = (Path(__file__).parent / f"{min_tweet_count}_{name}.edges").resolve()
    if os.path.isfile(edgelist):
        logging.info(f"{min_tweet_count}_{name}.edges already extracted")
    else:
        logging.info(
            f"Extracting '{name}' network for nodes with at least {min_tweet_count} tweets..."
        )

        with open(edgelist, "w") as f:
            for author1, author2 in tqdm(
                con.execute(edge_query.format(view), [min_tweet_count, min_tweet_count])
            ):
                f.write(f"{author1} {author2}\n")

    # Extract the edgelists of the subnetworks centered around each ego node
    G = nx.read_edgelist(edgelist, create_using=nx.Graph)
    for ego_node in ego_nodes:
        ego_edgelist = (
            Path(__file__).parent / f"{min_tweet_count}_{name}_{ego_node[1]}.edges"
        ).resolve()
        if os.path.isfile(ego_edgelist):
            logging.info(
                f"{min_tweet_count}_{name}_{ego_node[1]}.edges already extracted"
            )
        else:
            logging.info(
                f"Extracting '{name}' ego network of '{ego_node[1]}' for nodes with at least {min_tweet_count} tweets..."
            )
            ego_graph: nx.Graph = nx.ego_graph(G, ego_node[0])
            nx.write_edgelist(ego_graph, ego_edgelist, data=False)
