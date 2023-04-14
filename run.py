from os import chdir, path, listdir
from pandas import read_csv, concat

FOLDER = "/home/brandon/amazon_scraper"
chdir(FOLDER)
from scraper import new_browser, download_data

browser_box = []

# queries_file = path.join(FOLDER, "queries.csv")
search_results_folder = path.join(FOLDER, "search_results")

download_data(
    browser_box,
    path.join(FOLDER, "queries.csv"),
    search_results_folder
)

# piece together all search csvs into one csv
concat((
    read_csv(
        path.join(search_results_folder, file)
    ) for file in listdir(search_results_folder)
)).to_csv(path.join(FOLDER, "result.csv"), index = False)

browser_box[0].close()



