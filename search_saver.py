from datetime import datetime
from os import chdir, path
from pandas import DataFrame
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select

FOLDER = "/home/brandon/amazon_scraper"
chdir(FOLDER)
from utilities import (
    FoiledAgainError,
    get_filenames,
    new_browser,
    only,
    save_page,
    wait_for_amazon,
    WentWrongError
)

def find_department_option_index(browser, department):
    for index, option in enumerate(browser.find_elements(By.CSS_SELECTOR, "#searchDropdownBox option")):
        if option.text == department:
            return index
    raise Exception("Department " + department + " not found!")

# query = "fire hd 10 tablet"
# browser = new_browser(user_agents[0])
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
    while department_index < find_department_option_index(browser, department_selector.first_selected_option.text):
        department_menu.send_keys(Keys.UP)
    while department_index > find_department_option_index(browser, department_selector.first_selected_option.text):
        department_menu.send_keys(Keys.DOWN)
    
    search_bar = only(browser.find_elements(By.CSS_SELECTOR, "#twotabsearchtextbox"))

    search_bar.clear()
    search_bar.send_keys(query)
    search_bar.send_keys(Keys.RETURN)

    # wait until a new page starts loading
    wait_for_amazon(browser)

    # save a log with the time we ran the query
    DataFrame({"query": [query], "datetime": [datetime.now()]}).to_csv(
        path.join(search_logs_folder, search_id + ".csv"), index=False
    )

    # the CSS selector is for all the parts we don't need
    # save the page to the folder
    save_page(
        browser,
        "map, meta, noscript, script, style, svg, video, #rhf, span[data-component-type='s-filters-panel-view'], a[title='tab to skip to main search results'], #navbar-main, span[data-component-type='s-result-info-bar'], div[data-cel-widget*='MAIN-TEXT_REFORMULATION'], div[cel_widget_id*='MAIN-TEXT_REFORMULATION'], div[data-csa-c-painter='multi-brand-creative-desktop-cards'], #ape_Search_auto-bottom-advertising-0_portal-batch-fast-btf-loom_placement, #navFooter, div[data-cel-widget*='LEFT-SAFE_FRAME'], div.widgetId\\=loom-desktop-top-slot_automotive-part-finder, div[cel_widget_id*='MAIN-FEEDBACK'], div[cel_widget_id*='MAIN-PAGINATION']",
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

    # empty because there was no previous searched query
    # query = "chemistry textbook"
    # department = "Books"
    for department, query in zip(
        query_data.loc[:, "department"], query_data.loc[:, "query"]
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
                search_pages_folder
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

            try:
                save_search_page(
                    browser,
                    search_id,
                    department,
                    query,
                    search_logs_folder,
                    search_pages_folder
                )
            except TimeoutException:
                print(search_id)
                print("Timeout, skipping")
            except WentWrongError:
                print(search_id)
                print("Went wrong, skipping")
                go_to_amazon(browser)
        except TimeoutException:
            print(search_id)
            print("Timeout, skipping")
        except WentWrongError:
            print(search_id)
            print("Went wrong, skipping")
            go_to_amazon(browser)

    return user_agent_index
