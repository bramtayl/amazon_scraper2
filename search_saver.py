from datetime import datetime
from os import chdir, path
from pandas import DataFrame
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.expected_conditions import (
    presence_of_element_located as located,
)
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.wait import WebDriverWait as wait
datetime

FOLDER = "/home/brandon/amazon_scraper"
chdir(FOLDER)
from utilities import (
    check_captcha,
    FoiledAgainError,
    get_filenames,
    new_browser,
    only,
    save_page,
    WAIT_TIME,
)


def wait_for_search_bar(browser):
    wait(browser, WAIT_TIME).until(located((By.CSS_SELECTOR, "#twotabsearchtextbox")))


# we need this to check if a new page has loaded
def get_searched_query(browser):
    searched_query_css = "div.widgetId\\=result-info-bar span.a-color-state"
    return (
        wait(browser, WAIT_TIME)
        .until(
            located(
                (
                    By.CSS_SELECTOR,
                    # one for each version of the main screen
                    searched_query_css,
                )
            )
        )
        .text
    )


# query = "fire hd 10 tablet"
# browser = new_browser(USER_AGENT_LIST[0])
# department = "All Departments"
def save_search_page(
    browser,
    department,
    query,
    search_logs_folder,
    search_pages_folder,
    previous_searched_query,
):
    department_menu = only(browser.find_elements(By.CSS_SELECTOR, "#searchDropdownBox"))
    department_selector = Select(department_menu)
    if department != department_selector.first_selected_option.text:
        # we need to mess with the drop down to activate it I guess
        department_menu.send_keys(Keys.DOWN)
        department_selector.select_by_visible_text(department)

    search_bar = only(browser.find_elements(By.CSS_SELECTOR, "#twotabsearchtextbox"))

    search_bar.clear()
    search_bar.send_keys(query)
    search_bar.send_keys(Keys.RETURN)

    try:
        # wait until the new search has actually loaded
        wait(browser, WAIT_TIME).until(
            lambda browser: get_searched_query(browser) != previous_searched_query
        )
    except TimeoutError as an_error:
        # throw a custom error if there is a captcha
        check_captcha(browser)
        # otherwise, print the query for debugging, then raise the error
        print(query)
        raise an_error

    # this is at the bottom of the html so should load after all the search results
    wait(browser, WAIT_TIME).until(
        located((By.CSS_SELECTOR, "div.s-result-list-placeholder"))
    )

    # this is the text amazon displays, so could technically be different from the
    # original query
    # it's also quoted
    searched_query = get_searched_query(browser)

    # don't know what the placeholder is for but it seems to load after the search results?
    wait(browser, WAIT_TIME).until(
        located((By.CSS_SELECTOR, "div.s-result-list-placeholder"))
    )

    # save a log with the time we ran the query
    DataFrame({"query": [query], "datetime": [datetime.now()]}).to_csv(
        path.join(search_logs_folder, query + ".csv"), index=False
    )

    # the CSS selector is for all the parts we don't need
    # save the page to the folder
    save_page(
        browser,
        "map, meta, noscript, script, style, svg, video, #rhf, span[data-component-type='s-filters-panel-view'], a[title='tab to skip to main search results'], #navbar-main, span[data-component-type='s-result-info-bar'], div[data-cel-widget*='MAIN-TEXT_REFORMULATION'], div[cel_widget_id*='MAIN-TEXT_REFORMULATION'], div[data-csa-c-painter='multi-brand-creative-desktop-cards'], #ape_Search_auto-bottom-advertising-0_portal-batch-fast-btf-loom_placement, #navFooter, div[data-cel-widget*='LEFT-SAFE_FRAME'], div.widgetId\\=loom-desktop-top-slot_automotive-part-finder, div[cel_widget_id*='MAIN-FEEDBACK'], div[cel_widget_id*='MAIN-PAGINATION']",
        path.join(search_pages_folder, query + ".html"),
    )
    return searched_query


def go_to_amazon(browser):
    url = "https://www.amazon.com/"
    try:
        browser.get(url)
        wait_for_search_bar(browser)
    except TimeoutException:
        # try one more time
        # sometimes Amazon loads an abbreviated homepage without the full search bar
        browser.get(url)
        wait_for_search_bar(browser)


def save_search_pages(
    browser_box,
    query_data,
    search_logs_folder,
    search_pages_folder,
    user_agents,
    user_agent_index=0,
):
    completed_queries = get_filenames(search_pages_folder)

    browser = new_browser(user_agents[user_agent_index])
    browser_box.append(browser)

    go_to_amazon(browser)

    # empty because there was no previous searched query
    previous_searched_query = ""

    # query = "chemistry textbook"
    # department = "Books"
    for department, query in zip(
        query_data.loc[:, "department"], query_data.loc[:, "query"]
    ):
        # don't rerun a query we already ran
        if query in completed_queries:
            continue

        try:
            previous_searched_query = save_search_page(
                browser,
                department,
                query,
                search_logs_folder,
                search_pages_folder,
                previous_searched_query,
            )
        except FoiledAgainError:
            # if Amazon sends a captcha, change the user agent and try again
            user_agent_index = user_agent_index + 1
            # start again if we're at the end
            if user_agent_index == len(user_agent_index):
                user_agent_index = 0
            browser = new_browser(user_agent_index[user_agent_index])
            browser_box.append(browser)
            go_to_amazon(browser)

            # try one more time
            previous_searched_query = save_search_page(
                browser,
                department,
                query,
                search_logs_folder,
                search_pages_folder,
                previous_searched_query,
            )

    return user_agent_index
