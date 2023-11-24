# build pylucene first
# I used oracle JDK 17
# importing lucene enables a bunch of other imports
import lucene

from bs4 import BeautifulSoup
from java.nio.file import Paths
from os import listdir, mkdir, path
from org.apache.lucene.analysis.standard import StandardAnalyzer
from org.apache.lucene.document import Document, Field, StringField, TextField
from org.apache.lucene.index import DirectoryReader, IndexWriter, IndexWriterConfig
from org.apache.lucene.queryparser.classic import QueryParser
from org.apache.lucene.search import IndexSearcher
from org.apache.lucene.store import NIOFSDirectory
from pandas import concat, DataFrame

def get_filenames(folder):
    return [path.splitext(filename)[0] for filename in listdir(folder)]

def maybe_create(folder):
    if not path.isdir(folder):
        mkdir(folder)

def index_product_text(lucene_folder, ASIN, product_text):
    writer = IndexWriter(
        NIOFSDirectory(Paths.get(lucene_folder)), IndexWriterConfig(StandardAnalyzer())
    )
    print(ASIN)
    doc = Document()
    doc.add(Field("ASIN", ASIN, StringField.TYPE_STORED))
    doc.add(Field("product_text", product_text, TextField.TYPE_STORED))
    writer.addDocument(doc)
    writer.commit()
    writer.close()


def index_product_pages(lucene_folder, product_pages_folder):
    for ASIN in get_filenames(product_pages_folder):
        with open(
            path.join(product_pages_folder, ASIN + ".html"), "r", encoding="UTF-8"
        ) as io:
            index_product_text(lucene_folder, ASIN, BeautifulSoup(io, "lxml", from_encoding="UTF-8").prettify())


def get_relevance_data(lucene_folder, queries, number_of_matches):
    searcher = IndexSearcher(
        DirectoryReader.open(NIOFSDirectory(Paths.get(lucene_folder)))
    )
    parser = QueryParser("product_text", StandardAnalyzer())
    parser.setDefaultOperator(QueryParser.Operator.AND)

    results = []
    for query in queries:
        print(query)
        for score_data in searcher.search(parser.parse(query), number_of_matches).scoreDocs:
            results.append(
                DataFrame(
                    {
                        "query": [query],
                        "ASIN": [searcher.doc(score_data.doc)["ASIN"]],
                        "score": [score_data.score],
                    }
                )
            )

    del searcher
    return concat(results, ignore_index=True)
