from bs4 import BeautifulSoup
from datetime import datetime
from os import chdir, listdir, path
from pandas import DataFrame
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select

FOLDER = "/home/brandon/amazon_scraper"
chdir(FOLDER)
from src.utilities import (
    combine_folder_csvs,
    FoiledAgainError,
    get_filenames,
    new_browser,
    only,
    read_html,
    save_soup,
    wait_for_amazon,
    WentWrongError,
)


def find_department_option_index(browser, department):
    for index, option in enumerate(
        browser.find_elements(By.CSS_SELECTOR, "#searchDropdownBox option")
    ):
        if option.text == department:
            return index
    raise Exception("Department " + department + " not found!")


SEARCH_JUNK_SELECTORS = [
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
    "#similarities_feature_div",
    "#skiplink",
    "#storeDisclaimer_feature_div",
    "#va-related-videos-widget_feature_div",
    "#valuePick_feature_div",
    "#sims-themis-sponsored-products-2_feature_div",
    "#sponsoredProducts2_feature_div",
    ".reviews-display-ad",
    "div.fs-trusted-recos",
    "div#HLCXComparisonWidgetNonTechnical_feature_div",
]


# query = "fire hd 10 tablet"
# browser = new_browser(user_agents[0], fakespot = True)
# go_to_amazon(browser)
# department = "Books"
def save_search_page(
    browser,
    search_id,
    department,
    query,
    search_logs_folder,
    search_pages_folder,
):
    department_menu = only(browser.find_elements(By.CSS_SELECTOR, "#searchDropdownBox"))
    department_selector = Select(department_menu)
    department_index = find_department_option_index(browser, department)
    while department_index < find_department_option_index(
        browser, department_selector.first_selected_option.text
    ):
        department_menu.send_keys(Keys.UP)
    while department_index > find_department_option_index(
        browser, department_selector.first_selected_option.text
    ):
        department_menu.send_keys(Keys.DOWN)

    search_bar = only(browser.find_elements(By.CSS_SELECTOR, "#twotabsearchtextbox"))

    search_bar.clear()
    search_bar.send_keys(query)
    search_bar.send_keys(Keys.RETURN)

    # wait until a new page starts loading
    wait_for_amazon(browser)

    # save a log with the time we ran the query
    DataFrame(
        {"search_id": search_id, "datetime": datetime.now()}, index=[0]
    ).set_index("search_id").to_csv(path.join(search_logs_folder, search_id + ".csv"))

    # the CSS selector is for all the parts we don't need
    # save the page to the folder
    save_soup(
        BeautifulSoup(
            browser.page_source.encode("utf-8"), "lxml", from_encoding="UTF-8"
        ),
        SEARCH_JUNK_SELECTORS,
        path.join(search_pages_folder, search_id + ".html"),
    )


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


def reclean_search_pages(search_pages_folder):
    for file in listdir(search_pages_folder):
        save_soup(
            read_html(path.join(search_pages_folder, file)), SEARCH_JUNK_SELECTORS, file
        )


def save_search_pages(
    browser_box,
    query_data,
    search_logs_folder,
    search_pages_folder,
    user_agents,
    user_agent_index=0,
):
    completed_search_ids = get_filenames(search_pages_folder)

    browser = new_browser(user_agents[user_agent_index])
    browser_box.append(browser)

    go_to_amazon(browser)

    query_data["search_id"] = [
        department + "-" + query
        for (department, query) in zip(
            query_data.loc[:, "department"], query_data.loc[:, "query"]
        )
    ]

    # empty because there was no previous searched query
    # query = "chemistry textbook"
    # department = "Books"
    for department, query, search_id in zip(
        query_data.loc[:, "department"],
        query_data.loc[:, "query"],
        query_data.loc[:, "search_id"],
    ):
        search_id = department + "-" + query

        # don't rerun a query we already ran
        if search_id in completed_search_ids:
            continue

        try:
            save_search_page(
                browser,
                search_id,
                department,
                query,
                search_logs_folder,
                search_pages_folder,
            )
        except FoiledAgainError:
            browser.close()
            browser_box.clear()
            # if Amazon sends a captcha, change the user agent and try again
            user_agent_index = user_agent_index + 1
            # start again if we're at the end
            if user_agent_index == len(user_agent_index):
                user_agent_index = 0
            browser = new_browser(user_agent_index[user_agent_index])
            browser_box.append(browser)
            go_to_amazon(browser)

            try:
                save_search_page(
                    browser,
                    search_id,
                    department,
                    query,
                    search_logs_folder,
                    search_pages_folder,
                )
            except TimeoutException:
                print(search_id)
                print("Timeout, skipping")
            except WentWrongError:
                print(search_id)
                print("Went wrong, skipping")
                # we need to go back to amazon so we can keep searching
                go_to_amazon(browser)
        except TimeoutException:
            print(search_id)
            print("Timeout, skipping")
        except WentWrongError:
            print(search_id)
            print("Went wrong, skipping")
            # we need to go back to amazon so we can keep searching
            go_to_amazon(browser)
        
    browser.close()
    browser_box.clear()

    return (
        # add the search logs to the query data to make search data
        query_data.set_index("search_id").join(
            combine_folder_csvs(search_logs_folder, "search_id"), how="left"
        ),
        user_agent_index,
    )
