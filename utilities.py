from bs4 import BeautifulSoup, Comment
from os import listdir, path
import re
from pandas import concat, DataFrame, read_csv
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium import webdriver

# time for timed waits
WAIT_TIME = 20


# custom error if amazon stops us with captcha
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
    # throw an error if we wait too long
    browser.set_page_load_timeout(WAIT_TIME)

    return browser


# pandas concat seems to want all the dataframe keys to be in the same order
# so sort them first
def sorted_dataframe(dictionary):
    the_keys = list(dictionary.keys())
    the_keys.sort()
    sorted_dict = {key: dictionary[key] for key in the_keys}
    return DataFrame(sorted_dict, index=[0])


# turn a bunch of dicts to dataframe and concatenate
def dicts_to_dataframe(dictionaries):
    return concat(
        (sorted_dataframe(dictionary) for dictionary in dictionaries),
        ignore_index=True,
    )


# combine all the csvs in a folder into a dataframe
def combine_folder_csvs(folder):
    return concat(
        (read_csv(path.join(folder, file)) for file in listdir(folder)),
        ignore_index=True,
    )


# get the filenames in a folder, sans file extension
def get_filenames(folder):
    return set(path.splitext(filename)[0] for filename in listdir(folder))


# custom error if the page no longer exists
def check_captcha(browser):
    foiled_agains = browser.find_elements(
        By.CSS_SELECTOR, "form[action='/errors/validateCaptcha']"
    )
    if len(foiled_agains) > 0:
        only(foiled_agains)
        raise FoiledAgainError()


# amazon has a bunch of empty divs reserved for specific cases
# and empty divs of empty divs
# sometimes the only text is whitespace that html removes anyway
# just remove them all
def is_empty_div(thing):
    if isinstance(thing, str):
        # not none means there's only spaces
        return not (re.match(r"^[\s]+$", thing) is None)
    if thing.name != "div":
        return False
    return all(is_empty_div(child) for child in thing.contents)


def save_page(browser, junk_css, filename):
    page = BeautifulSoup(browser.page_source, features="lxml")
    for junk in page.select(junk_css):
        junk.extract()
    for comment in page(text=lambda text: isinstance(text, Comment)):
        comment.extract()
    for div in page.select("div"):
        if is_empty_div(div):
            div.extract()

    with open(filename, "w") as file:
        file.write(str(page))
