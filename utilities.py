from os import listdir, path
from pandas import concat, DataFrame, read_csv
from selenium.webdriver.firefox.options import Options
from selenium import webdriver

WAIT_TIME = 20


# throw an error if there isn't one and only one result
# important safety measure for CSS selectors
def only(list):
    count = len(list)
    if count != 1:
        raise IndexError(count)
    return list[0]


def new_browser(user_agent):
    options = Options()
    # add headless to avoid the visual display and speed things up
    # options.add_argument("-headless")
    options.set_preference("general.useragent.override", user_agent)
    # this helps pages load faster I guess?
    options.set_capability("pageLoadStrategy", "eager")

    browser = webdriver.Firefox(options=options)
    # selenium sputters when scripts run too long so set a timeout
    browser.set_script_timeout(WAIT_TIME)

    return browser


def sorted_dataframe(dictionary):
    the_keys = list(dictionary.keys())
    the_keys.sort()
    sorted_dict = {key: dictionary[key] for key in the_keys}
    return DataFrame(sorted_dict, index=[0])


def dicts_to_dataframe(dictionaries):
    return concat(
        (sorted_dataframe(dictionary) for dictionary in dictionaries),
        axis=0,
        ignore_index=True,
    )


def combine_folder_csvs(folder):
    return concat(
        (read_csv(path.join(folder, file)) for file in listdir(folder)),
        axis=0,
        ignore_index=True,
    )


def get_filenames(folder):
    return set(
        path.splitext(filename)[0] for filename in listdir(folder)
    )