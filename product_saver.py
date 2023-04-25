from datetime import datetime
from os import chdir, path
from pandas import DataFrame
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.expected_conditions import (
    presence_of_element_located as located,
)
from selenium.webdriver.support.wait import WebDriverWait as wait

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


# custom error if the page no longer exists
class GoneError(Exception):
    pass


# need this to check whether a new product has loaded
def get_product_name(browser):
    title_elements = browser.find_elements(
        By.CSS_SELECTOR,
        "span#productTitle, span.qa-title-text, h1[data-automation-id='title']",
    )
    if len(title_elements) > 0:
        return only(title_elements).text

    # if there's no text title, there might be a custom-formatted title image
    # the title is in the alt attribute
    return only(
        browser.find_elements(By.CSS_SELECTOR, "h1[data-testid='title-art'] img")
    ).get_attribute("alt")


# sets of choices that one can choose from
def get_choice_sets(browser):
    return browser.find_elements(
        By.CSS_SELECTOR, "#twister-plus-inline-twister > div.inline-twister-row"
    )


# if buy box hasn't fully loaded because its waiting for users to make a choice
def has_partial_buyboxes(browser):
    return len(browser.find_elements(By.CSS_SELECTOR, "#partialStateBuybox")) > 0


# TODO:
# ask-btf_feature_div is the Q&A section
# it might be nice for relevance to have but isn't showing up in the HTML anyway...
JUNK_CSS = "map, meta, noscript, script, style, svg, video, #ad-endcap-1_feature_div, #ad-display-center-1_feature_div, #amsDetailRight_feature_div, #aplusBrandStory_feature_div, #ask-btf_feature_div, #beautyRecommendations_feature_div, #discovery-and-inspiration_feature_div, #dp-ads-center-promo_feature_div, #dp-ads-center-promo-top_feature_div, #dp-ads-middle_feature_div, #gridgetWrapper, #HLCXComparisonWidget_feature_div, #imageBlock_feature_div, #navbar-main, #navFooter, #navtop, #nav-upnav, #percolate-ui-ilm_div, #postsSameBrandCard_feature_div, #product-ads-feedback_feature_div, #similarities_feature_div, #skiplink, #storeDisclaimer_feature_div, #va-related-videos-widget_feature_div, #valuePick_feature_div, #sims-themis-sponsored-products-2_feature_div, #sponsoredProducts2_feature_div, .reviews-display-ad"


def save_product_page(
    browser,
    product_id,
    url,
    old_product_name,
    product_logs_folder,
    product_pages_folder,
):
    browser.get("https://www.amazon.com" + url)
    DataFrame({"product_id": [product_id], "datetime": [datetime.now()]}).to_csv(
        path.join(product_logs_folder, str(product_id) + ".csv"), index=False
    )

    try:
        # wait for a new product
        wait(browser, WAIT_TIME).until(
            lambda browser: get_product_name(browser) != old_product_name
        )
    except IndexError as an_error:
        # the url might be old and no longer work
        gones = browser.find_elements(
            By.CSS_SELECTOR,
            "img[alt=\"Sorry! We couldn't find that page. Try searching or go to Amazon's home page.\"]",
        )
        if len(gones) > 0:
            # sanity check
            only(gones)
            # throw a custom error
            raise GoneError()

        # throw a custom error if there is a captcha
        check_captcha(browser)

        raise an_error

    product_name = get_product_name(browser)

    # this is at the bottom of the html so should load after all the rest of the page
    wait(browser, WAIT_TIME).until(located((By.CSS_SELECTOR, "div#navFooter")))

    # if buy box hasn't fully loaded because its waiting for users to make a choice
    if has_partial_buyboxes(browser):
        # select the first option for all the choice sets
        for choice_set_index in range(len(get_choice_sets(browser))):
            get_choice_sets(browser)[choice_set_index].find_elements(
                By.CSS_SELECTOR, "ul > li.a-declarative"
            )[0].click()

        # wait for the buybox to update
        wait(browser, WAIT_TIME).until(
            lambda browser: not (has_partial_buyboxes(browser))
        )

    # find the prefix for the first buy box, if there a couple of different one
    # there might be e.g. one for a new product, and one for a used product
    buyboxes = browser.find_elements(By.CSS_SELECTOR, "#buyBoxAccordion")
    if len(buyboxes) > 0:
        # sanity check
        only(buyboxes)
        # use data from the first buy box
        box_prefix = "#buyBoxAccordion > div:first-child "
    else:
        box_prefix = ""

    save_page(
        browser, JUNK_CSS, path.join(product_pages_folder, str(product_id) + ".html")
    )

    # if we have to pick a seller, save a second page with the seller list
    choose_seller_buttons = browser.find_elements(
        By.CSS_SELECTOR,
        box_prefix + "a[title='See All Buying Options']",
    )

    if len(choose_seller_buttons) > 0:
        # open the seller list
        only(choose_seller_buttons).click()

        # wait for the seller list to load
        wait(browser, WAIT_TIME).until(located((By.CSS_SELECTOR, "#aod-offer-list")))

        # save the second page
        save_page(
            browser,
            JUNK_CSS,
            path.join(product_pages_folder, str(product_id) + "-sellers.html"),
        )

    return product_name


# query = "chemistry textbook"
# browser = new_browser("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Safari/537.36")
# url = search_results.loc[:, "url"][1000]
def save_product_pages(
    browser_box,
    search_results_data,
    product_logs_folder,
    product_pages_folder,
    user_agents,
    user_agent_index=0,
):
    browser = new_browser(user_agents[user_agent_index])
    browser_box.append(browser)

    completed_product_ids = get_filenames(product_pages_folder)

    # no previous product, so starts empty
    old_product_name = ""
    for product_id, url in zip(
        search_results_data.loc[:, "product_id"], search_results_data.loc[:, "url"]
    ):
        # don't save a product we already have
        if str(product_id) in completed_product_ids:
            continue

        old_product_name = ""
        try:
            old_product_name = save_product_page(
                browser,
                product_id,
                url,
                old_product_name,
                product_logs_folder,
                product_pages_folder,
            )
        except GoneError:
            # if the product is gone, print some debug information, and just continue
            print(str(product_id) + ": " + url)
            print("Page no longer exists, skipping")
            continue
        except TimeoutException:
            # if the product times out, print some debug information, and just continue
            # come back to get it later
            print(str(product_id) + ": " + url)
            print("Timeout, skipping")
            continue
        except FoiledAgainError:
            # if Amazon sends a captcha, change the user agent and try again
            user_agent_index = user_agent_index + 1
            # start again if we're at the end
            if user_agent_index == len(user_agents):
                user_agent_index = 0
            browser = new_browser(user_agents[user_agent_index])
            browser_box.append(browser)
            try:
                old_product_name = save_product_page(
                    browser,
                    product_id,
                    url,
                    old_product_name,
                    product_logs_folder,
                    product_pages_folder,
                )
            # hande the errors above again, except for the FoiledAgain error
            # if there's still a captcha this time, just give up
            except GoneError:
                print(str(product_id) + ": " + url)
                print("Page no longer exists, skipping")
                continue
            except TimeoutException:
                print(str(product_id) + ": " + url)
                print("Timeout, skipping")
                continue

    return user_agent_index
