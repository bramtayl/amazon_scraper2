from bs4 import BeautifulSoup, Comment
from os import listdir, path
import re
from pandas import concat, DataFrame, read_csv
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.expected_conditions import (
    presence_of_element_located as located,
    invisibility_of_element_located as not_located,
)
from selenium.webdriver.support.wait import WebDriverWait as wait

# time for timed waits
WAIT_TIME = 20

FAKESPOT_FILE = "/home/brandon/snap/firefox/common/.mozilla/firefox/0tsz0chl.default/extensions/{44df5123-f715-9146-bfaa-c6e8d4461d44}.xpi"


# custom error if amazon stops us with captcha
class FoiledAgainError(Exception):
    pass


# custom error if the page no longer exists
class GoneError(Exception):
    pass

# custom error if amazon tells us something "went wrong"
class WentWrongError(Exception):
    pass

# custom error if there is not exactly one in a list
class NotExactlyOneError(Exception):
    pass


# throw an error if there isn't one and only one result
# important safety measure for CSS selectors
def only(list):
    if len(list) != 1:
        raise NotExactlyOneError()
    return list[0]


def new_browser(user_agent, fakespot=False):
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
    if fakespot:
        browser.execute("INSTALL_ADDON", {"path": FAKESPOT_FILE, "temporary": True})
        # wait for fakespot to open a new tab
        wait(browser, WAIT_TIME).until(lambda browser: len(browser.window_handles) > 1)
        # close it
        browser.switch_to.window(browser.window_handles[1])
        browser.close()
        # return to main tab
        browser.switch_to.window(browser.window_handles[0])

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


def wait_for_amazon(browser):
    try:
        # wait a couple of seconds for a new page to start not_located
        wait(browser, 2).until(not_located((By.CSS_SELECTOR, "#navFooter")))
    except TimeoutException:
        # if we time out, its already loaded
        pass

    try:
        wait(browser, WAIT_TIME).until(located((By.CSS_SELECTOR, "#navFooter")))
    except TimeoutException as an_error:
        foiled_agains = browser.find_elements(
            By.CSS_SELECTOR, "form[action='/errors/validateCaptcha']"
        )
        if len(foiled_agains) > 0:
            only(foiled_agains)
            raise FoiledAgainError()

        gones = browser.find_elements(
            By.CSS_SELECTOR,
            "img[alt=\"Sorry! We couldn't find that page. Try searching or go to Amazon's home page.\"]",
        )
        if len(gones) > 0:
            # sanity check
            only(gones)
            # throw a custom error
            raise GoneError()

        went_wrongs = browser.find_elements(
            By.CSS_SELECTOR,
            'img[alt="Sorry! Something went wrong on our end. Please go back and try again or go to Amazon\'s home page."]',
        )
        if len(went_wrongs) > 0:
            only(went_wrongs)
            raise WentWrongError()

        raise an_error
