from os import chdir, path
from pandas import read_csv

FOLDER = "/home/brandon/amazon_scraper"
chdir(FOLDER)
from utilities import combine_folder_csvs
from search_scraper import run_searches
from save_products import save_products

query_data = read_csv(path.join(FOLDER, "queries.csv"))
user_agents = read_csv(path.join(FOLDER, "user_agents.csv")).loc[:, "user_agent"]
browser_box = []

# queries_file = path.join(FOLDER, "queries.csv")
search_results_folder = path.join(FOLDER, "search_results")
product_pages_folder = path.join(FOLDER, "product_pages")

user_agent_index = 0
user_agent_index = run_searches(
    browser_box,
    query_data,
    search_results_folder,
    user_agents,
    user_agent_index=user_agent_index,
)

search_results = combine_folder_csvs(search_results_folder)

user_agent_index = save_products(
    browser_box,
    search_results,
    product_pages_folder,
    user_agents,
    user_agent_index=user_agent_index,
)

combine_folder_csvs(product_results_folder).to_csv("result.csv")

for browser in browser_box:
    browser.close()

# TODO:
# number of option boxes
# name of the selected option box
# number of sidebar boxes
# name of the selected sidebar box
# number of sellers (for items with multiple sellers)
# coupons
# seller name

# whether subscription available (done two formats maybe more out there)
# whether eligable for refund (doneish)
# whether bundles available (ignore maybe)

