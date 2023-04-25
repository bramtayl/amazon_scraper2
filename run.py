from os import chdir, path
from pandas import read_csv

FOLDER = "/home/brandon/amazon_scraper"
chdir(FOLDER)
from utilities import combine_folder_csvs
from save_searches import save_searches
from save_products import save_products
from product_scraper import scrape_products

browser_box = []

# TODO: product logs
query_data = read_csv(path.join(FOLDER, "data", "queries.csv"))
user_agents = read_csv(path.join(FOLDER, "user_agents.csv")).loc[:, "user_agent"]
search_logs_folder = path.join(FOLDER, "data", "search_logs")
search_pages_folder = path.join(FOLDER, "data", "search_pages")
search_results_folder = path.join(FOLDER, "data", "search_results")
product_pages_folder = path.join(FOLDER, "data", "product_pages")
product_results_folder = path.join(FOLDER, "data", "product_results")

user_agent_index = 4
user_agent_index = save_searches(
    browser_box,
    query_data,
    search_logs_folder,
    search_pages_folder,
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

for browser in browser_box:
    browser.close()

scrape_products(product_pages_folder).to_csv(path.join(FOLDER, "result.csv"))

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

# page no longer exists: https://www.amazon.com/gp/slredirect/picassoRedirect.html/ref=pa_sp_mtf_aps_sr_pg1_1?ie=UTF8&adId=A04276923NGE1Z8ZND0Z1&qualifier=1681822641&id=4761451586758343&widgetName=sp_mtf&url=%2FBondelid-Soccer-Jerseys-T-Shirt-Outdoor%2Fdp%2FB0BVB2DZVM%2Fref%3Dsr_1_38_sspa%3Fkeywords%3Dfc%2Bbarcelona%2Bjersey%26qid%3D1681822641%26sr%3D8-38-spons%26psc%3D1
# movie_title: https://www.amazon.com/Avatar-Way-Water-Sam-Worthington/dp/B0B72TVT92/ref=sr_1_14?keywords=dvd+movies&qid=1681822652&sr=8-14
# title is image: https://www.amazon.com/Wing-Prayer-Dennis-Quaid/dp/B0B75TB7H8/ref=sr_1_15?keywords=dvd+movies&qid=1681822652&sr=8-15
# total review count is a span: https://www.amazon.com/Metallic-Glitter-Comforter-Printed-Bedding/dp/B09CT6C3N9/ref=sr_1_54?keywords=queen+comforter+set&qid=1681822595&sr=8-54

