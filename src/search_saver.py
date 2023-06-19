from os import chdir, path
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

FOLDER = "/home/brandon/amazon_scraper"
chdir(FOLDER)
from src.utilities import (
    FoiledAgainError,
    get_filenames,
    new_browser,
    only,
    save_browser,
    switch_user_agent,
    wait_for_amazon,
    WentWrongError,
)

# query = "fire hd 10 tablet"
# browser = new_browser(user_agents[0], fakespot = True)
# go_to_amazon(browser)
# department = "Books"
def save_search_page(
    browser,
    query,
    search_pages_folder,
):

    search_bar = only(browser.find_elements(By.CSS_SELECTOR, "#twotabsearchtextbox"))

    search_bar.clear()
    search_bar.send_keys(query)
    search_bar.send_keys(Keys.RETURN)

    # wait until a new page starts loading
    wait_for_amazon(browser)

    # the CSS selector is for all the parts we don't need
    # save the page to the folder
    save_browser(
        browser,
        path.join(search_pages_folder, query + ".html"),
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
    queries,
    search_pages_folder,
    user_agents,
    user_agent_index=0,
):
    completed_queries = get_filenames(search_pages_folder)

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
            save_search_page(
                browser,
                query,
                search_pages_folder,
            )
        except FoiledAgainError:
            browser, user_agent_index = switch_user_agent(browser_box, browser, user_agents, user_agent_index)
            go_to_amazon(browser)

            try:
                save_search_page(
                    browser,
                    query,
                    search_pages_folder,
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
