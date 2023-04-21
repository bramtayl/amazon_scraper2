from os import chdir, listdir, path
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.expected_conditions import (
    presence_of_element_located as located,
)
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.wait import WebDriverWait as wait

FOLDER = "/home/brandon/amazon_scraper"
chdir(FOLDER)
from utilities import dicts_to_dataframe, new_browser, only, WAIT_TIME


def wait_for_search_bar(browser):
    wait(browser, WAIT_TIME).until(
        located(
            (
                By.CSS_SELECTOR,
                # one for each version of the main screen
                "#twotabsearchtextbox, #nav-bb-search",
            )
        )
    )


# amazon sometime gives an abbreviated version of the main page with no department dropdown
# reload until we get it
def try_search_page(browser, department, query):
    department_menus = browser.find_elements(By.CSS_SELECTOR, "#searchDropdownBox")

    if len(department_menus) == 0:
        browser.refresh()
        wait_for_search_bar(browser)
        return try_search_page(browser, department, query)

    department_menu = only(department_menus)
    print(query + ":")
    department_selector = Select(department_menu)
    if department != department_selector.first_selected_option.text:
        # we need to mess with the drop down to activate it I guess
        department_menu.send_keys(Keys.DOWN)
        department_selector.select_by_visible_text(department)

    search_bar = only(browser.find_elements(By.CSS_SELECTOR, "#twotabsearchtextbox"))

    search_bar.clear()
    search_bar.send_keys(query)
    search_bar.send_keys(Keys.RETURN)
    # don't know what the placeholder is for but it seems to load after the search results?
    wait(browser, WAIT_TIME).until(
        located((By.CSS_SELECTOR, "div.s-result-list-placeholder"))
    )

    return dicts_to_dataframe(
        parse_search_result(browser, query, index)
        for index in range(
            len(
                browser.find_elements(
                    By.CSS_SELECTOR,
                    "div.s-main-slot.s-result-list > div[data-component-type='s-search-result']",
                )
            )
        )
    )


def parse_search_result(browser, query, index):
    print("Parsing search result #{index}".format(index=index))
    product_data = {"search_term": query, "rank": index + 1}
    search_result = browser.find_elements(
        By.CSS_SELECTOR,
        "div.s-main-slot.s-result-list > div[data-component-type='s-search-result']",
    )[index]

    sponsored_tags = search_result.find_elements(
        By.CSS_SELECTOR, ".puis-label-popover-default"
    )
    if len(sponsored_tags) > 0:
        # sanity check
        only(sponsored_tags)
        product_data["ad"] = True

    product_data["url"] = only(
        search_result.find_elements(
            By.CSS_SELECTOR,
            # a link in a heading
            "h2 a",
        )
    ).get_attribute("href")

    limited_time_deal_label = search_result.find_elements(
        By.CSS_SELECTOR, "span[data-a-badge-color='sx-lighting-deal-red']"
    )
    
    if limited_time_deal_label is not None:
        only(limited_time_deal_label)
        product_data["limited_time_deal"] = True

    provenance_certifications = search_result.find_elements(
        By.XPATH, "//*[contains(@data-s-pc-popover, 'provenanceCertifications')]"
    )
    if len(provenance_certifications) > 0:
        product_data["provenance_certifications"] = provenance_certifications.text 

    images = search_result.find_elements(
        By.CSS_SELECTOR, "img[class='s-image']"
    )
    for image in images:
        if image.get_attribute("src") == "https://m.media-amazon.com/images/I/111mHoVK0kL._SS200_.png":
            product_data["small_business"] = True


    return product_data


# query = "fire hd 10 tablet"
# browser = new_browser(USER_AGENT_LIST[0])
# department = "All Departments"
def run_search(browser, department, query, search_results_folder):
    browser.get("https://www.amazon.com/")
    wait_for_search_bar(browser)
    search_results = try_search_page(browser, department, query)

    # possible there's no results
    if len(search_results) > 0:
        search_results.to_csv(
            path.join(search_results_folder, query + ".csv"), index=False
        )


# TODO: read the department from a csv instead
# department = "Books"
def run_searches(
    browser_box, query_data, search_results_folder, user_agents, user_agent_index=0
):
    completed_queries = set(
        (path.splitext(filename)[0] for filename in listdir(search_results_folder))
    )

    browser = new_browser(user_agents[user_agent_index])
    browser_box.append(browser)

    # query = "chemistry textbook"
    for department, category, query in zip(
        query_data.loc[:, "department"],
        query_data.loc[:, "category"],
        query_data.loc[:, "query"],
    ):
        if query in completed_queries:
            continue

        try:
            run_search(browser, department, query, search_results_folder)
        except Exception as an_error:
            # change the user agent and see if it works now
            foiled_agains = browser.find_elements(
                By.CSS_SELECTOR, "form[action='/errors/validateCaptcha']"
            )
            if len(foiled_agains) > 0:
                only(foiled_agains)
                user_agent_index = user_agent_index + 1
                if user_agent_index == len(user_agent_index):
                    user_agent_index = 0
                browser = new_browser(user_agent_index[user_agent_index])
                browser_box.append(browser)
                run_search(browser, department, query, search_results_folder)
            else:
                raise an_error

    return user_agent_index
