from bs4 import BeautifulSoup, Comment, NavigableString
from os import listdir, mkdir, path
import re
from pandas import concat, read_csv
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.expected_conditions import (
    presence_of_element_located as located,
    invisibility_of_element_located as not_located,
)
from selenium.webdriver.support.wait import WebDriverWait as wait

HEADLESS = False

JUNK_SELECTORS = [
    "iframe",
    "map",
    "meta",
    "noscript",
    "script",
    "style",
    "svg",
    "video",
    "#ad-endcap-1_feature_div",
    "#ad-display-center-1_feature_div",
    "#amsDetailRight_feature_div",
    "#aplusBrandStory_feature_div",
    "#beautyRecommendations_feature_div",
    "#discovery-and-inspiration_feature_div",
    "div#fs-confirm-modal",
    "div.fs-privacy-notice",
    "div.fs-trusted-recos",
    "div#HLCXComparisonWidgetNonTechnical_feature_div",
    "#dp-ads-center-promo_feature_div",
    "#dp-ads-center-promo-top_feature_div",
    "#dp-ads-middle_feature_div",
    "#gridgetWrapper",
    "#HLCXComparisonWidget_feature_div",
    "#imageBlock_feature_div",
    "#navbar-main",
    "#navFooter",
    "#navtop",
    "#nav-upnav",
    "#percolate-ui-ilm_div",
    "#postsSameBrandCard_feature_div",
    "#product-ads-feedback_feature_div",
    ".reviews-display-ad",
    "#similarities_feature_div",
    "#skiplink",
    "#storeDisclaimer_feature_div",
    "#va-related-videos-widget_feature_div",
    "#valuePick_feature_div",
    "#sims-themis-sponsored-products-2_feature_div",
    "#sponsoredProducts2_feature_div",
]

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
    number_of_items = len(list)
    if len(list) != 1:
        raise NotExactlyOneError(number_of_items)
    return list[0]


def new_browser(user_agent, fakespot=False):
    options = Options()
    # add headless to avoid the visual display and speed things up
    if HEADLESS:
        options.add_argument("-headless")
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


def switch_user_agent(browser_box, browser, user_agents, user_agent_index):
    browser.close()
    browser_box.clear()
    # if Amazon sends a captcha, change the user agent and try again
    if user_agent_index == len(user_agents) - 1:
        # start again if we're at the end
        new_user_agent_index = 0
    else:
        new_user_agent_index = user_agent_index + 1

    return (
        new_browser(user_agents[new_user_agent_index], fakespot=True),
        new_user_agent_index,
    )


# combine all the csvs in a folder into a dataframe
def combine_folder_csvs(folder, index_column):
    return concat(
        (
            read_csv(path.join(folder, file)).set_index(index_column)
            for file in listdir(folder)
        )
    )


# get the filenames in a folder, sans file extension
def get_filenames(folder):
    return [path.splitext(filename)[0] for filename in listdir(folder)]


# amazon has a bunch of empty divs reserved for specific cases
# and empty divs of empty divs
def is_empty_div(thing):
    if thing.name == "div":
        # empty will return true
        return all(is_empty_div(child) for child in thing.contents)
    return False


def remove_whitespace(soup):
    for text in soup(text=lambda text: isinstance(text, NavigableString)):
        stripped = text.strip()
        if stripped == "":
            text.extract()
        elif text != stripped:
            text.replace_with(stripped)

def get_clean_soup(browser):
    soup = BeautifulSoup(
        browser.page_source.encode("utf-8"), "lxml", from_encoding="UTF-8"
    )
    for junk in soup.select(", ".join(JUNK_SELECTORS)):
        junk.extract()
    for comment in soup(text=lambda text: isinstance(text, Comment)):
        comment.extract()
    remove_whitespace(soup)
    # only top-level divs
    for div in soup.select("div"):
        if is_empty_div(div):
            div.extract()
    return soup


# soup = product_page
def save_browser(browser, filename):
    with open(filename, "w", encoding="UTF-8") as io:
        io.write(get_clean_soup(browser).prettify())


def wait_for_amazon(browser):
    try:
        # wait a couple of seconds for a new page to start loading
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


def read_html(file):
    with open(file, "r", encoding="UTF-8") as io:
        soup = BeautifulSoup(io, "lxml", from_encoding="UTF-8")
        remove_whitespace(soup)
        return soup


# stole from https://github.com/django/django/blob/main/django/utils/text.py
def get_valid_filename(name):
    # replace spaces with underscores
    # remove anything that is not an alphanumeric, dash, underscore, or dot
    return name.replace("/", "%2F")


def maybe_create(folder):
    if not path.isdir(folder):
        mkdir(folder)


class RegexError(Exception):
    pass


def strict_match(regex, text):
    match = re.fullmatch(regex, text)
    if match == None:
        raise RegexError(regex + ": " + text)
    return match
