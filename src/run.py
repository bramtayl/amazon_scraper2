import lucene
from os import chdir, path
from pandas import read_csv
import subprocess

chdir("/home/brandon/amazon_scraper")

from src.utilities import maybe_create
from src.search_saver import save_search_pages
from src.product_saver import multithread_save_product_pages
from src.product_parser import parse_product_pages
from src.utilities import combine_folder_csvs

CURRENT_YEAR = 2023
THREADS = 3

inputs_folder = "inputs"
user_agents = read_csv(path.join(inputs_folder, "user_agents.csv")).loc[:, "user_agent"]
queries = read_csv(path.join(inputs_folder, "queries.csv")).loc[:, "query"]
all_queries = read_csv(path.join(inputs_folder, "all_queries.csv")).loc[:, "query"]

results_folder = "results"
maybe_create(results_folder)

search_results_folder = path.join(results_folder, "search_results")
maybe_create(search_results_folder)

duplicate_results_folder = path.join(results_folder, "duplicate_results")
maybe_create(duplicate_results_folder)

product_pages_folder = path.join(results_folder, "product_pages")
maybe_create(product_pages_folder)

search_data_file = path.join(results_folder, "search_data.csv")
duplicates_data_file = path.join(results_folder, "duplicates_data.csv")
product_ASINs_file = path.join(results_folder, "product_ASINs_data.csv")
already_searched_file = path.join(results_folder, "already_searched.csv")

user_agent_index = 60

# user_agent_index = save_search_pages(
#     queries,
#     search_results_folder,
#      already_searched_file,
#     user_agents,
#     user_agent_index=user_agent_index,
# )

# combine_folder_csvs(search_results_folder).to_csv(search_data_file, index=False)


# user_agent_index = save_search_pages(
#     all_queries,
#     duplicate_results_folder,
#     already_searched_file,
#     user_agents,
#     user_agent_index=user_agent_index,
#     require_complete=True
# )


# combine_folder_csvs(duplicate_results_folder).to_csv(duplicates_data_file, index=False)

# search_data = read_csv(search_data_file)

# search_data[["ASIN"]].drop_duplicates().to_csv(product_ASINs_file, index=False)

# product_data = read_csv(product_ASINs_file)

# multithread_save_product_pages(
#     THREADS,
#     user_agents,
#     product_data.loc[:, "ASIN"].sample(frac=1),
#     product_pages_folder,
# )

parse_product_pages(product_pages_folder, CURRENT_YEAR).to_csv(
    path.join(results_folder, "product_data.csv"), index = False
)

subprocess.run([
    "docker", "run",
    "--name", "pylucene",
    "--mount", "type=bind,source=/home/brandon/amazon_scraper,target=/amazon_scraper",
    "coady/pylucene",
    "python3", "/amazon_scraper/lucene/run.py"
])
subprocess.run([
    "docker", "rm", "pylucene"
])

