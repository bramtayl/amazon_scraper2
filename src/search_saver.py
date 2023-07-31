from os import chdir, path
from pandas import concat, DataFrame, read_csv
import re
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.expected_conditions import (
    presence_of_element_located as located
)
from selenium.webdriver.support.wait import WebDriverWait as wait
from time import sleep
from urllib3.exceptions import ProtocolError
from urllib.parse import unquote


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


RELATIVE_TOLERANCE = 0.1


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

RESULT_COUNT_SELECTOR = "div[data-cel-widget='UPPER-RESULT_INFO_BAR-0'] div.s-breadcrumb div.a-spacing-top-small span:first-child"

def get_result_count_match(browser):
    wait(browser, 2).until(located((By.CSS_SELECTOR, RESULT_COUNT_SELECTOR)))
    return re.fullmatch("\d+-(\d+) of (\d+) results for", only(browser.find_elements(By.CSS_SELECTOR, RESULT_COUNT_SELECTOR)).text)

# query = "laptop"
# browser = new_browser("Mozilla/5.0 (X11; OpenBSD amd64; rv:28.0) Gecko/20100101 Firefox/28.0", fakespot = True)
# go_to_amazon(browser)
# require_complete = true
def run_query(
    browser,
    query,
    search_results_folder,
    already_searched,
    require_complete
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
    if require_complete and get_result_count_match(browser) is None:
        already_searched.add(query)
        return
    next_page_buttons = get_next_page_buttons(browser, page_number)
    while next_page_buttons:
        if not next_page_buttons:
            print(str(page_number))
        only(next_page_buttons).click()
        wait_for_amazon(browser)
        if require_complete and get_result_count_match(browser) is None:
            already_searched.add(query)
            return
        add_page(page_tables, browser, query, page_number)
        page_number = page_number + 1
        next_page_buttons = get_next_page_buttons(browser, page_number)
    
    all_together = concat(page_tables)
    if require_complete:
        result_count_match = get_result_count_match(browser)
        if result_count_match is None:
            already_searched.add(query)
            return
        if result_count_match.group(1) != result_count_match.group(2):
            already_searched.add(query)
            return
    
    all_together.to_csv(path.join(search_results_folder, query + ".csv"))

def run_query_save(
    browser,
    query,
    search_results_folder,
    already_searched,
    already_searched_file,
    require_complete
):
    run_query(
        browser,
        query,
        search_results_folder,
        already_searched,
        require_complete
    )
    DataFrame({"query": list(already_searched)}).to_csv(already_searched_file, index = False)
    

def save_search_pages(
    queries,
    search_results_folder,
    already_searched_file,
    user_agents,
    user_agent_index=0,
    require_complete=False
):
    browser = new_browser(user_agents[user_agent_index])

    already_searched = set(read_csv(already_searched_file).loc[:, "query"])

    go_to_amazon(browser)

    # empty because there was no previous searched query
    # query = "chemistry textbook"
    # department = "Books"
    for query in queries:
        # don't rerun a query we already ran
        if query in already_searched:
            continue

        try:
            run_query_save(
                browser,
                query,
                search_results_folder,
                already_searched,
                already_searched_file,
                require_complete
            )
        except FoiledAgainError:
            browser, user_agent_index = switch_user_agent(
                browser, user_agents, user_agent_index
            )
            go_to_amazon(browser)

            try:
                run_query_save(
                    browser,
                    query,
                    search_results_folder,
                    already_searched,
                    already_searched_file,
                    require_complete
                )
            except ProtocolError:
                print("WiFi dropped, sleeping and skipping")
                sleep(60)
            except TimeoutException:
                print(query)
                print("Timeout, skipping")
            except WentWrongError:
                print(query)
                print("Went wrong, skipping")
                # we need to go back to amazon so we can keep searching
                go_to_amazon(browser)
        except ProtocolError:
            print("WiFi dropped, sleeping and skipping")
            sleep(60)
        except TimeoutException:
            print(query)
            print("Timeout, skipping")
        except WentWrongError:
            print(query)
            print("Went wrong, skipping")
            # we need to go back to amazon so we can keep searching
            go_to_amazon(browser)

    browser.close()

    return user_agent_index
