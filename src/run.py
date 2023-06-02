import lucene
from os import path
from pandas import read_csv
from src.utilities import maybe_create, combine_folder_csvs
from src.search_saver import save_search_pages
from src.search_parser import parse_search_pages
from src.product_saver import save_product_pages
from src.product_parser import parse_product_pages
from src.relevance import index_product_pages, get_relevance_data

CURRENT_YEAR = 2023

inputs_folder = "inputs"
user_agents = read_csv(path.join(inputs_folder, "user_agents.csv")).loc[:, "user_agent"]
query_data = read_csv(path.join(inputs_folder, "queries.csv"))

results_folder = "results"
maybe_create(results_folder)

searches_folder = path.join(results_folder, "searches")
maybe_create(searches_folder)

search_logs_folder = path.join(searches_folder, "logs")
maybe_create(search_logs_folder)

search_pages_folder = path.join(searches_folder, "pages")
maybe_create(search_pages_folder)

products_folder = path.join(results_folder, "products")
maybe_create(products_folder)

product_logs_folder = path.join(products_folder, "logs")
maybe_create(product_logs_folder)

product_pages_folder = path.join(products_folder, "pages")
maybe_create(product_pages_folder)

product_urls_file = path.join(products_folder, "product_url_data.csv")

lucene_folder = path.join(products_folder, "lucene")
maybe_create(lucene_folder)

browser_box = []
user_agent_index = 1

search_data, user_agent_index = save_search_pages(
    browser_box,
    query_data,
    search_logs_folder,
    search_pages_folder,
    user_agents,
    user_agent_index=user_agent_index,
)

search_data.to_csv(path.join(searches_folder, "searches.csv"))

parse_search_pages(search_pages_folder).to_csv(product_urls_file)

product_url_data = read_csv(product_urls_file).set_index("product_id")

user_agent_index = save_product_pages(
    browser_box,
    product_url_data,
    product_logs_folder,
    product_pages_folder,
    user_agents,
    user_agent_index=user_agent_index,
)

combine_folder_csvs(product_logs_folder, "product_id").to_csv(
    path.join(products_folder, "product_logs.csv")
)

(product_data, category_data, best_seller_data) = parse_product_pages(
    product_pages_folder, CURRENT_YEAR
)

product_data.to_csv(path.join(products_folder, "products.csv"))
category_data.to_csv(path.join(products_folder, "categories.csv"))
best_seller_data.to_csv(path.join(products_folder, "best_sellers.csv"))

lucene.initVM(vmargs=["-Djava.awt.headless=true"])

index_product_pages(lucene_folder, product_pages_folder, product_url_data.index)

get_relevance_data(lucene_folder, query_data.loc[:, "query"]).to_csv(
    path.join(products_folder, "relevance.csv"), index = False
)
