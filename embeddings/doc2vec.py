import logging
import multiprocessing
import os
import gensim
from corpus import TweetCorpus

logging.basicConfig(
    format="%(asctime)s : %(levelname)s : %(message)s", level=logging.INFO
)

corpus = TweetCorpus()

if not os.path.isfile("models/doc2vec.model"):
    model = gensim.models.doc2vec.Doc2Vec(
        vector_size=200,
        dm=0,
        epochs=10,
        min_count=2,
        workers=multiprocessing.cpu_count(),
    )
    model.build_vocab(corpus)
    model.save("models/doc2vec.model")
else:
    model: gensim.models.doc2vec.Doc2Vec = gensim.models.doc2vec.Doc2Vec.load(
        "models/doc2vec.model"
    )
    model.init_weights()

model.train(corpus, total_examples=model.corpus_count, epochs=model.epochs)
model.save("models/doc2vec.model")
