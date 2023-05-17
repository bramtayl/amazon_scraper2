from os import path
from pandas import read_csv
from src.utilities import maybe_create
from src.search_saver import save_search_pages
from src.search_parser import parse_search_pages
from src.product_saver import save_product_pages
from src.product_parser import parse_product_pages

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

(product_data, category_data, best_seller_data) = parse_product_pages(
    product_url_data, product_pages_folder, product_logs_folder, CURRENT_YEAR
)


product_data.to_csv(path.join(products_folder, "products.csv"))
category_data.to_csv(path.join(products_folder, "categories.csv"))
best_seller_data.to_csv(path.join(products_folder, "best_sellers.csv"))
