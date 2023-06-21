from os import chdir, path
from pandas import concat, DataFrame
import re
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import urllib

FOLDER = "/home/brandon/amazon_scraper"
chdir(FOLDER)
from src.utilities import (
    FoiledAgainError,
    get_clean_soup,
    get_filenames,
    new_browser,
    only,
    switch_user_agent,
    wait_for_amazon,
    WentWrongError,
)


class NoASINError(Exception):
    pass


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
        decoded_url = urllib.parse.unquote(raw_product_url)
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
            "rank": [index + 1],
            "ASIN": [ASIN],
            "sponsored": [sponsored],
            "amazon_brand": [amazon_brand],
        }
    )


def add_page(page_tables, browser, query, page_number):
    page_tables.append(concat(
        parse_search_result(query, search_result, page_number, index)
        for index, search_result in enumerate(
            get_clean_soup(browser).select(
                ", ".join(
                    [
                        "div.s-main-slot.s-result-list > div[data-component-type='s-search-result']",
                        "div.s-main-slot.s-result-list > div[cel_widget_id*='MAIN-VIDEO_SINGLE_PRODUCT']",
                    ]
                )
            )
        )
    ))

def get_next_page_buttons(browser, page_number):
    return browser.find_elements(By.CSS_SELECTOR, "a[aria-label='Go to page " + str(page_number) + "']")

# query = "fire hd 10 tablet"
# browser = new_browser(user_agents[0], fakespot = True)
# go_to_amazon(browser)
# department = "Books"
def run_query(
    browser,
    query,
    search_results_folder,
):
    search_bar = only(browser.find_elements(By.CSS_SELECTOR, "#twotabsearchtextbox"))

    search_bar.clear()
    search_bar.send_keys(query)
    search_bar.send_keys(Keys.RETURN)

    # wait until a new page starts loading
    wait_for_amazon(browser)

    # the CSS selector is for all the parts we don't need
    # save the page to the folder
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
            
    concat(page_tables).to_csv(path.join(search_results_folder, query + ".csv"))

def go_to_amazon(browser):
    url = "https://www.amazon.com/"
    try:
        browser.get(url)
        wait_for_amazon(browser)
    except TimeoutException:
        # try one more time
        # sometimes Amazon loads an abbreviated homepage without the full search bar
        browser.get(url)
        wait_for_amazon(browser)


def save_search_pages(
    browser_box,
    queries,
    search_results_folder,
    user_agents,
    user_agent_index=0,
):
    completed_queries = get_filenames(search_results_folder)

    browser = new_browser(user_agents[user_agent_index])
    browser_box.append(browser)

    go_to_amazon(browser)

    # empty because there was no previous searched query
    # query = "chemistry textbook"
    # department = "Books"
    for query in queries:
        # don't rerun a query we already ran
        if query in completed_queries:
            continue

        try:
            run_query(
                browser,
                query,
                search_results_folder,
            )
        except FoiledAgainError:
            browser, user_agent_index = switch_user_agent(
                browser_box, browser, user_agents, user_agent_index
            )
            go_to_amazon(browser)

            try:
                run_query(
                    browser,
                    query,
                    search_results_folder,
                )
            except TimeoutException:
                print(query)
                print("Timeout, skipping")
            except WentWrongError:
                print(query)
                print("Went wrong, skipping")
                # we need to go back to amazon so we can keep searching
                go_to_amazon(browser)
        except TimeoutException:
            print(query)
            print("Timeout, skipping")
        except WentWrongError:
            print(query)
            print("Went wrong, skipping")
            # we need to go back to amazon so we can keep searching
            go_to_amazon(browser)

    browser.close()
    browser_box.clear()

    return user_agent_index
