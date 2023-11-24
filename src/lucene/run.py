import lucene
from os import path
from lucene.relevance import index_product_pages, get_relevance_data, maybe_create
from pandas import read_csv

inputs_folder = "inputs"

queries = read_csv(path.join(inputs_folder, "queries.csv")).loc[:, "query"]

results_folder = "results"

lucene_folder = path.join(results_folder, "lucene")
maybe_create(lucene_folder)

product_pages_folder = path.join(results_folder, "product_pages")


lucene.initVM(vmargs=["-Djava.awt.headless=true"])

index_product_pages(lucene_folder, product_pages_folder)

get_relevance_data(lucene_folder, queries, product_data.shape[0]).to_csv(
    path.join(results_folder, "relevance_data.csv"), index=False
)