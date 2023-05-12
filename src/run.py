from os import path, mkdir
from pandas import read_csv
from src.search_saver import save_search_pages
from src.search_parser import parse_search_pages
from src.product_saver import save_product_pages
from src.product_parser import find_products, parse_product_pages

inputs_folder = "inputs"
queries_data = read_csv(path.join(inputs_folder, "queries.csv"))
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

search_results_file = path.join(searches_folder, "searches.csv")

products_folder = path.join(results_folder, "products")
if not path.isdir(products_folder):
    mkdir(products_folder)

product_logs_folder = path.join(products_folder, "logs")
if not path.isdir(product_logs_folder):
    mkdir(product_logs_folder)

product_pages_folder = path.join(products_folder, "pages")
if not path.isdir(product_pages_folder):
    mkdir(product_pages_folder)

product_results_file = path.join(products_folder, "products.csv")
best_seller_results_file = path.join(products_folder, "best_sellers.csv")
category_results_file = path.join(products_folder, "categories.csv")

browser_box = []
user_agent_index = 0

user_agent_index = save_search_pages(
    browser_box,
    read_csv(path.join("inputs", "queries.csv")),
    path.join("results", "search_logs"),
    search_pages_folder,
    user_agents,
    user_agent_index=user_agent_index,
)

parse_search_pages(search_pages_folder).to_csv(search_results_file, index = False)

user_agent_index = save_product_pages(
    browser_box,
    queries_data,
    product_logs_folder,
    product_pages_folder,
    user_agents,
    user_agent_index=user_agent_index,
)

for browser in browser_box:
    browser.close()

find_products(product_pages_folder, lambda product_page, sellers_page: len(product_page.select("#desktop_qualifiedBuyBox #amazonGlobal_feature_div > .a-color-secondary")) > 0)

# new
# used
# sns
# renewed
# audibleCash
# audibleUpsell
# deals
parse_product_pages(
    product_pages_folder,
    product_results_file,
    best_seller_results_file,
    category_results_file
)


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

# UTF encoding

# page no longer exists: https://www.amazon.com/gp/slredirect/picassoRedirect.html/ref=pa_sp_mtf_aps_sr_pg1_1?ie=UTF8&adId=A04276923NGE1Z8ZND0Z1&qualifier=1681822641&id=4761451586758343&widgetName=sp_mtf&url=%2FBondelid-Soccer-Jerseys-T-Shirt-Outdoor%2Fdp%2FB0BVB2DZVM%2Fref%3Dsr_1_38_sspa%3Fkeywords%3Dfc%2Bbarcelona%2Bjersey%26qid%3D1681822641%26sr%3D8-38-spons%26psc%3D1
# movie_title: https://www.amazon.com/Avatar-Way-Water-Sam-Worthington/dp/B0B72TVT92/ref=sr_1_14?keywords=dvd+movies&qid=1681822652&sr=8-14
# title is image: https://www.amazon.com/Wing-Prayer-Dennis-Quaid/dp/B0B75TB7H8/ref=sr_1_15?keywords=dvd+movies&qid=1681822652&sr=8-15
# total review count is a span: https://www.amazon.com/Metallic-Glitter-Comforter-Printed-Bedding/dp/B09CT6C3N9/ref=sr_1_54?keywords=queen+comforter+set&qid=1681822595&sr=8-54
# number of reviews, not ratings