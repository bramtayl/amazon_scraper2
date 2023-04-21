from os import chdir, path
from selenium.webdriver.common.by import By
from selenium.webdriver.support.expected_conditions import (
    presence_of_element_located as located,
)
from selenium.webdriver.support.wait import WebDriverWait as wait
from bs4 import BeautifulSoup, Comment
import re

FOLDER = "/home/brandon/amazon_scraper"
chdir(FOLDER)
from utilities import get_filenames, new_browser, only, WAIT_TIME

def get_product_name(browser):
    return only(
        browser.find_elements(By.CSS_SELECTOR, "span#productTitle, span.qa-title-text")
    ).text

# sets of choices that one can choose from
def get_choice_sets(browser):
    return browser.find_elements(
        By.CSS_SELECTOR, "#twister-plus-inline-twister > div.inline-twister-row"
    )

# if buy box hasn't fully loaded because its waiting for users to make a choice
def has_partial_buyboxes(browser):
    return len(browser.find_elements(By.CSS_SELECTOR, "#partialStateBuybox")) > 0

def is_empty_string(thing):
    if isinstance(thing, str):
        if not(re.search(r"^[\s]+$", thing) is None):
            return True
    return False

def is_empty_div(thing):
    if isinstance(thing, str):
        # not none means there's only spaces
        return not(re.match(r"^[\s]+$", thing) is None)
    if thing.name != "div":
        return False
    return all(is_empty_div(child) for child in thing.contents)

def save_page(browser, filename):
    page = BeautifulSoup(browser.page_source, features = "lxml")
    # TODO:
    # ask-btf_feature_div is the Q&A section
    # it would be nice to have but isn't showing up in the HTML anyway...
    for junk in page.select('img, map, meta, noscript, script, style, svg, video, #ad-endcap-1_feature_div, #ad-display-center-1_feature_div, #amsDetailRight_feature_div, #aplusBrandStory_feature_div, #ask-btf_feature_div, #beautyRecommendations_feature_div, #discovery-and-inspiration_feature_div, #dp-ads-center-promo_feature_div, #dp-ads-center-promo-top_feature_div, #dp-ads-middle_feature_div, #gridgetWrapper, #HLCXComparisonWidget_feature_div, #imageBlock_feature_div, #navbar-main, #navFooter, #navtop, #nav-upnav, #percolate-ui-ilm_div, #postsSameBrandCard_feature_div, #product-ads-feedback_feature_div, #similarities_feature_div, #skiplink, #storeDisclaimer_feature_div, #va-related-videos-widget_feature_div, #valuePick_feature_div, #sims-themis-sponsored-products-2_feature_div, #sponsoredProducts2_feature_div, .reviews-display-ad'):
        junk.extract()
    for comment in page(text=lambda text: isinstance(text, Comment)):
        comment.extract()
    for div in page.select('div'):
        if is_empty_div(div):
            div.extract()

    with open(filename, "w") as file:
        file.write(str(page))

def try_save_product(browser, product_index, product_url, old_product_name, product_pages_folder):
    browser.get(product_url)

    # wait for a new product
    wait(browser, WAIT_TIME).until(
        lambda browser: get_product_name(browser) != old_product_name
    )
    # wait for the bottom of the product page to load
    wait(browser, WAIT_TIME).until(located((By.CSS_SELECTOR, "div#navFooter")))

    product_name = get_product_name(browser)
    old_product_name = product_name

    if has_partial_buyboxes(browser):
        # make all selections
        for choice_set_index in range(len(get_choice_sets(browser))):
            get_choice_sets(browser)[choice_set_index].find_elements(
                By.CSS_SELECTOR, "ul > li.a-declarative"
            )[0].click()

        # wait for the buybox to update
        wait(browser, WAIT_TIME).until(
            lambda browser: not (has_partial_buyboxes(browser))
        )
    
    buyboxes = browser.find_elements(By.CSS_SELECTOR, "#buyBoxAccordion")
    if len(buyboxes) > 0:
        # sanity check
        only(buyboxes)
        # use data from the first side box
        box_prefix = "#buyBoxAccordion > div:first-child "
    else:
        box_prefix = ""
    
    save_page(browser, path.join(product_pages_folder, str(product_index) + ".html"))
    
    choose_seller_buttons = browser.find_elements(
        By.CSS_SELECTOR,
        box_prefix + "a[title='See All Buying Options']",
    )

    if len(choose_seller_buttons) > 0:
        only(choose_seller_buttons).click()

        wait(browser, WAIT_TIME).until(
            located((By.CSS_SELECTOR, "#aod-offer-list"))
        )

        save_page(browser, path.join(product_pages_folder, str(product_index) + "-sellers.html"))

# query = "chemistry textbook"
# browser = new_browser("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Safari/537.36")
# product_url = search_results.loc[:, "url"][1000]
def save_products(
    browser_box,
    search_results_data,
    product_pages_folder,
    user_agents,
    user_agent_index=0,
):
    browser = new_browser(user_agents[user_agent_index])
    browser_box.append(browser)

    completed_product_indices = get_filenames(product_pages_folder)

    # no previous product, so starts empty
    old_product_name = ""
    for (product_index, product_url) in enumerate(search_results_data.loc[:, "url"]):
        
        if str(product_index) in completed_product_indices:
            continue
        
        if product_index % 50 != 0:
            continue

        print(str(product_index) + ": " + product_url)

        try:
            try_save_product(
                browser, product_index, product_url, old_product_name, product_pages_folder
            )
        except Exception as an_error:
            # change the user agent and see if it works now
            foiled_agains = browser.find_elements(
                By.CSS_SELECTOR, "form[action='/errors/validateCaptcha']"
            )
            if len(foiled_agains) > 0:
                only(foiled_agains)
                user_agent_index = user_agent_index + 1
                if user_agent_index == len(user_agents):
                    user_agent_index = 0
                browser = new_browser(user_agents[user_agent_index])
                browser_box.append(browser)
                try_save_product(
                    browser, product_index, product_url, old_product_name, product_pages_folder
                )
            else:
                raise an_error

    return user_agent_index
