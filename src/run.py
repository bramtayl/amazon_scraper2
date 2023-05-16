from os import path, mkdir
from pandas import read_csv
from src.utilities import combine_folder_csvs
from src.search_saver import save_search_pages
from src.search_parser import parse_search_pages
from src.product_saver import save_product_pages
from src.product_parser import parse_product_pages

CURRENT_YEAR = 2023

inputs_folder = "inputs"
user_agents = read_csv(path.join(inputs_folder, "user_agents.csv")).loc[:, "user_agent"]

results_folder = "results"
if not path.isdir(results_folder):
    mkdir(results_folder)

searches_folder = path.join(results_folder, "searches")
if not path.isdir(searches_folder):
    mkdir(searches_folder)

search_logs_folder = path.join(searches_folder, "logs")
if not path.isdir(search_logs_folder):
    mkdir(search_logs_folder)

search_pages_folder = path.join(searches_folder, "pages")
if not path.isdir(search_pages_folder):
    mkdir(search_pages_folder)

products_folder = path.join(results_folder, "products")
if not path.isdir(products_folder):
    mkdir(products_folder)

product_logs_folder = path.join(products_folder, "logs")
if not path.isdir(product_logs_folder):
    mkdir(product_logs_folder)

product_pages_folder = path.join(products_folder, "pages")
if not path.isdir(product_pages_folder):
    mkdir(product_pages_folder)


browser_box = []
user_agent_index = 1

user_agent_index = save_search_pages(
    browser_box,
    read_csv(path.join(inputs_folder, "queries.csv")),
    search_logs_folder,
    search_pages_folder,
    user_agents,
    user_agent_index=user_agent_index,
)

# save the combined search logs
combine_folder_csvs(search_logs_folder).to_csv(
    path.join(searches_folder, "search_logs.csv"), index=False
)
search_results_data = parse_search_pages(search_pages_folder)

user_agent_index = save_product_pages(
    browser_box,
    search_results_data.loc[:, "product_url"],
    product_logs_folder,
    product_pages_folder,
    user_agents,
    user_agent_index=user_agent_index,
)

for browser in browser_box:
    browser.close()

(product_data, category_data, best_seller_data) = parse_product_pages(
    product_pages_folder, CURRENT_YEAR
)

category_data.to_csv(path.join(products_folder, "categories.csv"), index=False)

best_seller_data.to_csv(path.join(products_folder, "best_sellers.csv"), index=False)

# add the product data and product logs into the search results data, then save
search_results_data.set_index("product_filename").join(
    product_data.set_index("product_filename"), how="left"
).join(
    combine_folder_csvs(product_logs_folder).set_index("product_filename"), how="left"
).to_csv(
    path.join(products_folder, "products.csv"), index=False
)
