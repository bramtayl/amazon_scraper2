import lucene
from os import path
from pandas import read_csv
from src.utilities import maybe_create
from src.search_saver import save_search_pages
from src.product_saver import save_product_pages
from src.product_parser import parse_product_pages
from src.relevance import index_product_pages, get_relevance_data
from src.utilities import combine_folder_csvs

CURRENT_YEAR = 2023

inputs_folder = "inputs"
user_agents = read_csv(path.join(inputs_folder, "user_agents.csv")).loc[:, "user_agent"]
queries = read_csv(path.join(inputs_folder, "queries.csv")).loc[:, "query"]

results_folder = "results"
maybe_create(results_folder)

search_results_folder = path.join(results_folder, "search_results")
maybe_create(search_results_folder)

product_pages_folder = path.join(results_folder, "product_pages")
maybe_create(product_pages_folder)

search_data_file = path.join(results_folder, "search_data.csv")
product_ASINs_file = path.join(results_folder, "product_ASINs_data.csv")

lucene_folder = path.join(results_folder, "lucene")
maybe_create(lucene_folder)

browser_box = []
user_agent_index = 5

user_agent_index = save_search_pages(
    browser_box,
    queries,
    search_results_folder,
    user_agents,
    user_agent_index=user_agent_index,
)

combine_folder_csvs(search_results_folder).to_csv(search_data_file, index=False)

search_data = read_csv(search_data_file)

search_data[["ASIN"]].drop_duplicates().to_csv(
    product_ASINs_file, index=False
)

# randomly shuffle the products to help avoid detection?
product_ASINs = read_csv(product_ASINs_file).loc[:, "ASIN"].sample(frac = 1)

user_agent_index = save_product_pages(
    browser_box,
    product_ASINs,
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
