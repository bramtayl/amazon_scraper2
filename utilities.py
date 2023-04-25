from bs4 import BeautifulSoup, Comment
from os import listdir, path
import re
from pandas import concat, DataFrame, read_csv
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium import webdriver

WAIT_TIME = 20

class FoiledAgainError(Exception):
    pass


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
    browser.set_page_load_timeout(WAIT_TIME)

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

def check_captcha(browser):
    foiled_agains = browser.find_elements(
        By.CSS_SELECTOR, "form[action='/errors/validateCaptcha']"
    )
    if len(foiled_agains) > 0:
        only(foiled_agains)
        raise FoiledAgainError()

def is_empty_div(thing):
    if isinstance(thing, str):
        # not none means there's only spaces
        return not(re.match(r"^[\s]+$", thing) is None)
    if thing.name != "div":
        return False
    return all(is_empty_div(child) for child in thing.contents)

def save_page(browser, junk_css, filename):
    page = BeautifulSoup(browser.page_source, features = "lxml")
    # TODO:
    # ask-btf_feature_div is the Q&A section
    # it would be nice to have but isn't showing up in the HTML anyway...
    for junk in page.select(junk_css):
        junk.extract()
    for comment in page(text=lambda text: isinstance(text, Comment)):
        comment.extract()
    for div in page.select('div'):
        if is_empty_div(div):
            div.extract()

    with open(filename, "w") as file:
        file.write(str(page))