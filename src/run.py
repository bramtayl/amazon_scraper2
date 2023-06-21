import lucene
from os import path
from pandas import read_csv
from src.utilities import maybe_create
from src.search_saver import save_search_pages
from src.search_parser import parse_search_pages
from src.product_saver import save_product_pages
from src.product_parser import parse_product_pages
from src.relevance import index_product_pages, get_relevance_data

CURRENT_YEAR = 2023

inputs_folder = "inputs"
user_agents = read_csv(path.join(inputs_folder, "user_agents.csv")).loc[:, "user_agent"]
queries = read_csv(path.join(inputs_folder, "queries.csv")).loc[:, "query"]

results_folder = "results"
maybe_create(results_folder)

search_pages_folder = path.join(results_folder, "search_pages")
maybe_create(search_pages_folder)

product_pages_folder = path.join(results_folder, "product_pages")
maybe_create(product_pages_folder)

search_data_file = path.join(results_folder, "search_data.csv")
product_url_file = path.join(results_folder, "product_url_data.csv")

lucene_folder = path.join(results_folder, "lucene")
maybe_create(lucene_folder)

browser_box = []
user_agent_index = 0

user_agent_index = save_search_pages(
    browser_box,
    queries,
    search_pages_folder,
    user_agents,
    user_agent_index=user_agent_index,
)

parse_search_pages(search_pages_folder).to_csv(search_data_file, index=False)

search_data = read_csv(search_data_file)

search_data[["ASIN", "url_name"]].drop_duplicates().to_csv(
    product_url_file, index=False
)



product_url_data = read_csv(product_url_file)

class DuplicateASINs(Exception):
    pass

if len(set(product_url_data.loc[:, "ASIN"])) != product_url_data.shape[0]:
    raise DuplicateASINs()

user_agent_index = save_product_pages(
    browser_box,
    product_url_data,
    product_pages_folder,
    user_agents,
    user_agent_index=user_agent_index,
)

parse_product_pages(product_pages_folder, CURRENT_YEAR).to_csv(
    path.join(results_folder, "product_data.csv")
)


lucene.initVM(vmargs=["-Djava.awt.headless=true"])

index_product_pages(lucene_folder, product_pages_folder)

get_relevance_data(lucene_folder, queries).to_csv(
    path.join(results_folder, "relevance_data.csv"), index=False
)
