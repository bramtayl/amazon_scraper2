from datetime import datetime
from os import chdir, path
from pandas import DataFrame
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import MoveTargetOutOfBoundsException, TimeoutException
from selenium.webdriver.support.expected_conditions import (
    presence_of_element_located as located,
)
from selenium.webdriver.support.wait import WebDriverWait as wait

FOLDER = "/home/brandon/amazon_scraper"
chdir(FOLDER)
from utilities import (
    FoiledAgainError,
    GoneError,
    get_filenames,
    new_browser,
    only,
    save_page,
    wait_for_amazon,
    WAIT_TIME,
)


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
JUNK_CSS = "map, meta, noscript, script, style, svg, video, #ad-endcap-1_feature_div, #ad-display-center-1_feature_div, #amsDetailRight_feature_div, #aplusBrandStory_feature_div, #beautyRecommendations_feature_div, #discovery-and-inspiration_feature_div, #dp-ads-center-promo_feature_div, #dp-ads-center-promo-top_feature_div, #dp-ads-middle_feature_div, #gridgetWrapper, #HLCXComparisonWidget_feature_div, #imageBlock_feature_div, #navbar-main, #navFooter, #navtop, #nav-upnav, #percolate-ui-ilm_div, #postsSameBrandCard_feature_div, #product-ads-feedback_feature_div, #similarities_feature_div, #skiplink, #storeDisclaimer_feature_div, #va-related-videos-widget_feature_div, #valuePick_feature_div, #sims-themis-sponsored-products-2_feature_div, #sponsoredProducts2_feature_div, .reviews-display-ad"


# url = product_url_data.loc[:, "url"][0]
def save_product_page(
    browser,
    product_id,
    url,
    product_logs_folder,
    product_pages_folder,
):
    if url.startswith("http"):
        browser.get(url)
    else:
        browser.get("https://www.amazon.com" + url)
    
    DataFrame({"product_id": [product_id], "datetime": [datetime.now()]}).to_csv(
        path.join(product_logs_folder, product_id + ".csv"), index=False
    )

    wait_for_amazon(browser)
    try:
        # wait for fakespot grade
        wait(browser, WAIT_TIME).until(
            located((By.CSS_SELECTOR, "div.fakespot-main-grade-box-wrapper"))
        )
    except TimeoutException:
        # might not be a fakespot grade
        pass

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

    # Q&A only loads when it's view
    answers = browser.find_elements(
        By.CSS_SELECTOR, "div[data-cel-widget='ask-btf_feature_div']"
    )
    if len(answers) > 0:
        # scroll the Q&A into view
        browser.execute_script("arguments[0].scrollIntoView();", only(answers))
        # wait for the Q&A
        wait(browser, WAIT_TIME).until(
            located((By.CSS_SELECTOR, "div.askInlineWidget"))
        )

    save_page(
        browser, JUNK_CSS, path.join(product_pages_folder, product_id + ".html")
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
            path.join(product_pages_folder, product_id + "-sellers.html"),
        )


def save_product_pages(
    browser_box,
    product_url_data,
    product_logs_folder,
    product_pages_folder,
    user_agents,
    user_agent_index=0,
):
    browser = new_browser(user_agents[user_agent_index], fakespot=True)
    browser_box.append(browser)

    completed_product_ids = get_filenames(product_pages_folder)

    # no previous product, so starts empty
    # url = product_url_data.loc[:, "url"][0]
    for product_id, url in zip(
        product_url_data.loc[:, "product_id"], product_url_data.loc[:, "url"]
    ):
        # don't save a product we already have
        if product_id in completed_product_ids:
            continue

        try:
            save_product_page(
                browser,
                product_id,
                url,
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
            browser = new_browser(user_agents[user_agent_index], fakespot=True)
            browser_box.append(browser)
            try:
                save_product_page(
                    browser,
                    product_id,
                    url,
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
