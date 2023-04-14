from os import chdir, path, listdir
from pandas import read_csv, concat

FOLDER = "/home/brandon/amazon_scraper"
chdir(FOLDER)
from scraper import download_data

browser_box = []

# queries_file = path.join(FOLDER, "queries.csv")
search_results_folder = path.join(FOLDER, "search_results")

download_data(
    browser_box,
    path.join(FOLDER, "queries.csv"),
    search_results_folder,
    first_user_agent_index = 6
)

# browser = browser_box[1]

# piece together all search csvs into one csv
concat(
    (read_csv(
        path.join(search_results_folder, file)
    ) for file in listdir(search_results_folder)),
    axis = 0,
    ignore_index = True
).to_csv(path.join(FOLDER, "result.csv"), index = False)

browser_box[0].close()



