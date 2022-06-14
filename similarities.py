from itertools import combinations, product
import os
import networkx as nx
import logging
from pathlib import Path
import gensim
from runstats import Statistics
from tqdm import tqdm

NETWORK_TYPES = ["retweet", "quote", "reply", "mention"]
EGO_NODES = ["RT_com", "KyivPost", "SputnikInt", "KyivIndependent", "MoscowTimes"]


def print_stats(stats: Statistics):
    logging.info(f"Mean similarity:    {stats.mean()}")
    logging.info(f"Standard deviation: {stats.stddev()}")
    logging.info(f"Variance:           {stats.variance()}")
    print()


def intra_network_similarities(model: gensim.models.doc2vec.Doc2Vec, min_tweet_count):
    logging.info("Intra-network Similarities")
    for network_type in NETWORK_TYPES:
        for ego in EGO_NODES:
            logging.info(
                f"{ego} '{network_type}' network for nodes with at least {min_tweet_count} tweets..."
            )

            edgelist = (
                Path(__file__).parent
                / f"networks/{min_tweet_count}_{network_type}_{ego}.edges"
            ).resolve()
            G: nx.Graph = nx.read_edgelist(edgelist, create_using=nx.Graph)

            logging.info("All pair Similarities")
            num_pairs = len(list(combinations(G.nodes, 2)))
            stats = Statistics()
            for node1, node2 in tqdm(combinations(G.nodes, 2), total=num_pairs):
                stats.push(model.dv.similarity(node1, node2))
            print_stats(stats)

            logging.info("Neighbor similarities")
            edge_count = G.number_of_edges()
            stats = Statistics()
            for edge in tqdm(G.edges(), total=edge_count):
                stats.push(model.dv.similarity(edge[0], edge[1]))
            print_stats(stats)

            logging.info("Non-neighbor similarities")
            non_edge_count = (
                G.number_of_nodes() * (G.number_of_nodes() - 1) / 2
            ) - edge_count
            stats = Statistics()
            for non_edge in tqdm(nx.non_edges(G), total=non_edge_count):
                stats.push(model.dv.similarity(non_edge[0], non_edge[1]))
            print_stats(stats)


def inter_network_similarities(model: gensim.models.doc2vec.Doc2Vec, min_tweet_count):
    logging.info("Inter-network Similarities")
    for network_type in NETWORK_TYPES:
        for ego1, ego2 in combinations(EGO_NODES, 2):
            logging.info(
                f"({ego1} x {ego2}) '{network_type}' networks for nodes with at least {min_tweet_count} tweets..."
            )

            edgelist1 = (
                Path(__file__).parent
                / f"networks/{min_tweet_count}_{network_type}_{ego1}.edges"
            ).resolve()
            edgelist2 = (
                Path(__file__).parent
                / f"networks/{min_tweet_count}_{network_type}_{ego2}.edges"
            ).resolve()
            G1: nx.Graph = nx.read_edgelist(edgelist1, create_using=nx.Graph)
            G2: nx.Graph = nx.read_edgelist(edgelist2, create_using=nx.Graph)

            # Remove nodes existing in both networks
            G_intersection = nx.intersection(G1, G2)
            G1.remove_nodes_from(G_intersection.nodes)
            G2.remove_nodes_from(G_intersection.nodes)

            logging.info(f"Removed {G_intersection.number_of_nodes()} common nodes")

            num_pairs = len(list(product(G1.nodes, G2.nodes)))
            logging.info(f"Calculating similarities for {num_pairs} pairs")

            stats = Statistics()

            for node1, node2 in tqdm(product(G1.nodes, G2.nodes), total=num_pairs):
                stats.push(model.dv.similarity(node1, node2))
            print_stats(stats)


if __name__ == "__main__":

    min_tweet_count = None
    while not min_tweet_count:
        try:
            min_tweet_count = int(input("Minimum tweet count: "))
            for network_type in NETWORK_TYPES:
                for ego in EGO_NODES:
                    file = (
                        Path(__file__).parent
                        / f"networks/{min_tweet_count}_{network_type}_{ego}.edges"
                    ).resolve()

                    if not os.path.exists(file):
                        print(f"{file} does not exist. Aborting")
                        exit()
        except ValueError:
            continue

    logging.basicConfig(
        format="%(asctime)s : %(levelname)s : %(message)s", level=logging.INFO
    )
    logger = logging.getLogger()
    logfile_handler = logging.FileHandler(
        Path(__file__).parent / f"{min_tweet_count}_similarities.log"
    )
    logger.addHandler(logfile_handler)

    model_filepath = (
        Path(__file__).parent / "embeddings/models/doc2vec.model"
    ).resolve()
    model: gensim.models.doc2vec.Doc2Vec = gensim.models.doc2vec.Doc2Vec.load(
        str(model_filepath)
    )

    intra_network_similarities(model, min_tweet_count)
    inter_network_similarities(model, min_tweet_count)
