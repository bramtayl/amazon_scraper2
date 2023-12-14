from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
from selenium.webdriver.firefox.service import Service
from numpy import array_split
from os import listdir, mkdir, path
import re
from pandas import concat, DataFrame, read_csv
import re
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support.expected_conditions import (
    presence_of_element_located as located,
    invisibility_of_element_located as not_located,
)
from selenium.webdriver.support.wait import WebDriverWait as wait
from urllib.parse import unquote

PROFILES = [
    "wwmcnst4.default-esr",
    "c8kfuqs1.default-esr",
    "uei0gf7s.default-esr",
    "ztcu41pu.default-esr"
]

DRIVER_FILE = path.join(
    "C:\\",
    "Users",
    "ucbvbta",
    "geckodriver.exe"
)
HEADLESS = True
NUMBER_OF_LAPTOPS = 4
NUMBER_OF_THREADS = 2
WAIT_TIME = 20

# custom error if amazon stops us with captcha
class FoiledAgainError(Exception):
    pass


# custom error if the page no longer exists
class GoneError(Exception):
    pass


class NoASINError(Exception):
    pass


# custom error if there is not exactly one in a list
class NotExactlyOneError(Exception):
    pass


class RegexError(Exception):
    pass


# custom error if amazon tells us something "went wrong"
class WentWrongError(Exception):
    pass

class NoFakespotFile(Exception):
    pass


# throw an error if there isn't one and only one result
# important safety measure for CSS selectors
def only(list):
    number_of_items = len(list)
    if len(list) != 1:
        raise NotExactlyOneError(number_of_items)
    return list[0]


def open_browser(laptop_thread_index, fakespot_file, user_agent_index, fakespot):
    options = Options()
    # add headless to avoid the visual display and speed things up
    if HEADLESS:
        options.add_argument("-headless")
    options.set_preference(
        "general.useragent.override",
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.{0}) Gecko/20100101 Firefox/119.{1}".format(
            laptop_thread_index, user_agent_index
        )
    )
    # this helps pages load faster I guess?
    options.set_capability("pageLoadStrategy", "eager")

    browser = webdriver.Firefox(
        service=Service(DRIVER_FILE), options=options
    )
    # selenium sputters when scripts run too long so set a timeout
    browser.set_script_timeout(WAIT_TIME)
    # throw an error if we wait too long
    browser.set_page_load_timeout(WAIT_TIME)
    if fakespot:
        browser.execute("INSTALL_ADDON", {"path": fakespot_file, "temporary": True})
        # wait for fakespot to open a new tab
        wait(browser, WAIT_TIME).until(lambda browser: len(browser.window_handles) > 1)
        # close it
        browser.switch_to.window(browser.window_handles[1])
        browser.close()
        # return to main tab
        browser.switch_to.window(browser.window_handles[0])

    return browser


def switch_user_agent(browser, laptop_thread_index, fakespot_file, user_agent_index, fakespot):
    browser.close()
    new_user_agent_index = user_agent_index + 1
    return (
        open_browser(laptop_thread_index, fakespot_file, user_agent_index, fakespot),
        new_user_agent_index,
    )

def combine_folder_csvs(folder):
    return concat((read_csv(path.join(folder, file)) for file in listdir(folder)))


def get_filenames(folder):
    return [path.splitext(filename)[0] for filename in listdir(folder)]

def save_browser(browser, filename):
    with open(filename, "w", encoding="UTF-8") as io:
        io.write(browser.page_source)

def wait_for_amazon(browser):
    try:
        wait(browser, 2).until(not_located((By.CSS_SELECTOR, "#navFooter, #nav-ftr-copyright")))
        wait(browser, WAIT_TIME).until(located((By.CSS_SELECTOR, "#navFooter, #nav-ftr-copyright")))
    except TimeoutException as an_error:
        foiled_agains = browser.find_elements(
            By.CSS_SELECTOR, "form[action='/errors/validateCaptcha']"
        )
        if len(foiled_agains) > 0:
            only(foiled_agains)
            raise FoiledAgainError()

def maybe_create(folder):
    if not path.isdir(folder):
        mkdir(folder)

def strict_match(regex, text):
    match = re.fullmatch(regex, text)
    if match == None:
        raise RegexError(regex + ": " + text)
    return match


def get_soup(browser):
    return BeautifulSoup(
        browser.page_source.encode("utf-8"), "lxml", from_encoding="UTF-8"
    )


URL_PATTERN = r".*\/dp\/([^/]*)\/"


# index = 0
# file = open(path.join(search_results_folder, query + ".html"), "r", encoding='UTF-8')
# search_result = read_html(search_results_folder, query).select("div.s-main-slot.s-result-list > div[data-component-type='s-search-result']")[index]
# file.close()
def parse_search_result(query, search_result, page_number, index):
    sponsored = False
    sponsored_tags = search_result.select(
        "a[aria-label='View Sponsored information or leave ad feedback']"
    )
    if len(sponsored_tags) > 0:
        # sanity check
        only(sponsored_tags)
        sponsored = True

    raw_product_url = only(
        search_result.select(
            # a link in a heading
            "h2 a",
        )
    )["href"]

    regular_url_match = re.match(URL_PATTERN, raw_product_url)
    if not regular_url_match is None:
        ASIN = regular_url_match.group(1)
    else:
        decoded_url = unquote(raw_product_url)
        encoded_url_match = re.match(URL_PATTERN, decoded_url)
        if not encoded_url_match is None:
            ASIN = encoded_url_match.group(1)
        else:
            raise NoASINError(raw_product_url + " " + decoded_url)

    amazon_brand_widgets = search_result.select(".puis-light-weight-text")
    if len(amazon_brand_widgets):
        amazon_brand = True
    else:
        amazon_brand = False

    return DataFrame(
        {
            "query": [query],
            "page_number": [page_number],
            "page_rank": [index + 1],
            "ASIN": [ASIN],
            "sponsored": [sponsored],
            "amazon_brand": [amazon_brand],
        }
    )


def add_page(page_tables, browser, query, page_number):
    page_tables.append(
        concat(
            parse_search_result(query, search_result, page_number, index)
            for index, search_result in enumerate(
                get_soup(browser).select(
                    ", ".join(
                        [
                            "div.s-main-slot.s-result-list > div[data-component-type='s-search-result']",
                            "div.s-main-slot.s-result-list > div[cel_widget_id*='MAIN-VIDEO_SINGLE_PRODUCT']",
                        ]
                    )
                )
            )
        )
    )


def get_next_page_buttons(browser, page_number):
    return browser.find_elements(
        By.CSS_SELECTOR, "a[aria-label='Go to page " + str(page_number) + "']"
    )


def go_to_amazon(browser):
    url = "https://www.amazon.com/"
    browser.get(url)
    wait_for_amazon(browser)


def run_query(browser, query, search_file_name, new_browser = False):
    if new_browser:
        wait(browser, WAIT_TIME).until(
            located((By.CSS_SELECTOR, "input[data-action-type='DISMISS']"))
        )
        only(browser.find_elements(By.CSS_SELECTOR, "input[data-action-type='DISMISS']")).click()
    
    search_bar = only(browser.find_elements(By.CSS_SELECTOR, "#twotabsearchtextbox"))

    search_bar.clear()
    search_bar.send_keys(query)
    search_bar.send_keys(Keys.RETURN)

    wait_for_amazon(browser)
    
    page_number = 1

    page_tables = []

    add_page(page_tables, browser, query, page_number)
    page_number = page_number + 1
    next_page_buttons = get_next_page_buttons(browser, page_number)
    while next_page_buttons:
        if not next_page_buttons:
            print(str(page_number))
        only(next_page_buttons).click()
        wait_for_amazon(browser)
        add_page(page_tables, browser, query, page_number)
        page_number = page_number + 1
        next_page_buttons = get_next_page_buttons(browser, page_number)

    concat(page_tables).to_csv(search_file_name, index=False)


# product_url = product_url_data.loc[:, "product_url"][0]
def save_product_page(browser, ASIN, product_file_name, new_browser=False):
    browser.get("https://www.amazon.com/dp/" + ASIN)

    wait_for_amazon(browser)
    if new_browser:
        wait(browser, WAIT_TIME).until(
            located((By.CSS_SELECTOR, "button#fs-confirm-modal-ok-button"))
        )
        only(browser.find_elements(By.CSS_SELECTOR, "button#fs-confirm-modal-ok-button")).click()

        wait(browser, WAIT_TIME).until(
            located((By.CSS_SELECTOR, "input[data-action-type='DISMISS']"))
        )
        only(browser.find_elements(By.CSS_SELECTOR, "input[data-action-type='DISMISS']")).click()

    wait(browser, WAIT_TIME).until(
        located((By.CSS_SELECTOR, "div.fakespot-main-grade-box-wrapper"))
    )

    save_browser(
        browser,
        product_file_name,
    )

def save_search_pages(
    queries,
    search_results_folder,
    product_pages_folder,
    number_of_laptops,
    laptop_id,
    number_of_threads,
    thread_id,
    user_agent_index=0,
):
    fakespot_file = path.join(
        "C:\\",
        "Users",
        "ucbvbta",
        "AppData",
        "Roaming",
        "Mozilla",
        "Firefox",
        "Profiles",
        PROFILES[laptop_id],
        "extensions",
        "{44df5123-f715-9146-bfaa-c6e8d4461d44}.xpi"
    )

    if not path.exists(fakespot_file):
        raise NoFakespotFile(fakespot_file)

    laptop_thread_index = laptop_id * number_of_threads + thread_id
    queries = array_split(queries, number_of_laptops * number_of_threads)[
        laptop_thread_index
    ]

    browser = open_browser(laptop_thread_index, fakespot_file, user_agent_index, False)
    go_to_amazon(browser)
    new_browser = True
    for query in queries:
        search_file_name = path.join(search_results_folder, query + ".csv")
        if not path.exists(search_file_name):
            print("laptop-thread {0} saving search {1}".format(laptop_thread_index, query))
            try:
                run_query(browser, query, search_file_name, new_browser = new_browser)
                new_browser = False
            except BaseException as an_error:
                print(an_error)
                browser, user_agent_index = switch_user_agent(browser, laptop_thread_index, fakespot_file, user_agent_index, False)
                new_browser = True
                try:
                    run_query(browser, query, search_file_name, new_browser = new_browser)
                    new_browser = False
                except BaseException as an_error:
                    print(an_error)

        if not path.exists(search_file_name):
            return

        browser = open_browser(laptop_thread_index, fakespot_file, user_agent_index, fakespot=True)
        new_browser = True
        for ASIN in read_csv(search_file_name).loc[:, "ASIN"]:
            product_file_name = path.join(product_pages_folder, ASIN + ".html")
            if not path.exists(product_file_name):
                print("laptop-thread {0} saving ASIN {1}".format(laptop_thread_index, ASIN))
                try:
                    save_product_page(browser, ASIN, product_file_name, new_browser)
                    new_browser = False
                except BaseException as an_error:
                    print(an_error)
                    browser, user_agent_index = switch_user_agent(browser, laptop_thread_index, user_agent_index, False)
                    new_browser = True
                    try:
                        save_product_page(browser, ASIN, product_file_name, new_browser)
                        new_browser = False
                    except BaseException as an_error:
                        print(an_error)

def setup():
    inputs_folder = "inputs"
    queries = read_csv(path.join(inputs_folder, "all_queries.csv")).loc[:, "query"]

    results_folder = "results"
    maybe_create(results_folder)

    search_results_folder = path.join(results_folder, "search_results")
    maybe_create(search_results_folder)

    product_pages_folder = path.join(results_folder, "product_pages")
    maybe_create(product_pages_folder)

    return (queries, search_results_folder, product_pages_folder)


def multithread_save_product_pages(
    queries,
    search_results_folder,
    product_pages_folder,
    laptop_id,
    number_of_laptops = NUMBER_OF_LAPTOPS,
    number_of_threads = NUMBER_OF_THREADS
):
    with ThreadPoolExecutor() as executor:
        for result in executor.map(
            lambda thread_id: save_search_pages(
                queries,
                search_results_folder,
                product_pages_folder,
                number_of_laptops,
                laptop_id,
                number_of_threads,
                thread_id,
            ),
            range(number_of_threads),
        ):
            print(result)
