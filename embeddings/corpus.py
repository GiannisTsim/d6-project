import sqlite3
import gensim
from nltk.tokenize import TweetTokenizer
from pathlib import Path


class TweetCorpus:
    def __init__(self):
        db_filepath = (Path(__file__).parent / "../data/tweet.db").resolve()
        self.con = sqlite3.connect(db_filepath, check_same_thread=False)
        self.tokenizer = TweetTokenizer(
            preserve_case=False, reduce_len=True, strip_handles=False
        )

    def __iter__(self):
        query = """
            SELECT  AuthorId    AS Tag,
                    Tweet       AS Document
            FROM Tweet_Text_V
            WHERE Lang = 'en'
        """
        for tag, document in self.con.execute(query):
            yield gensim.models.doc2vec.TaggedDocument(
                self.tokenizer.tokenize(document),
                [tag],
            )
