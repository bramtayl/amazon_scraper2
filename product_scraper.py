from os import chdir, path
from re import search
from selenium.webdriver.common.by import By
from selenium.webdriver.support.expected_conditions import (
    presence_of_element_located as located,
)
from selenium.webdriver.support.wait import WebDriverWait as wait

FOLDER = "/home/brandon/amazon_scraper"
chdir(FOLDER)
from utilities import dicts_to_dataframe, new_browser, only, WAIT_TIME


# e.g. 1,000 -> 1000
def remove_commas(a_string):
    return a_string.replace(",", "")


def get_price(price_widget):
    # some prices have separate dollar and cent parts
    dollar_parts = price_widget.find_elements(By.CSS_SELECTOR, ".a-price-whole")
    if len(dollar_parts) > 0:
        # dollars
        return (
            int(
                remove_commas(
                    only(
                        price_widget.find_elements(By.CSS_SELECTOR, ".a-price-whole")
                    ).text
                )
                # cents
            )
            + int(
                remove_commas(
                    only(
                        price_widget.find_elements(By.CSS_SELECTOR, ".a-price-fraction")
                    ).text
                )
            )
            / 100
        )
    else:
        # others are all together
        return parse_price(price_widget.text)


def parse_price(price_string):
    # ignore the dollar sign in front
    return float(remove_commas(price_string[1:]))


def get_star_percentage(histogram_row):
    return only(
        histogram_row.find_elements(By.CSS_SELECTOR, ".a-text-right > .a-size-base")
    ).text


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


def get_histogram_rows(browser):
    return browser.find_elements(
        By.CSS_SELECTOR, ".cr-widget-TitleRatingsHistogram .a-histogram-row"
    )


def try_parse_product(browser, product_url, old_product_name):
    product_data = {}
    browser.get(product_url)

    # wait for a new product
    wait(browser, WAIT_TIME).until(
        lambda browser: get_product_name(browser) != old_product_name
    )
    # wait for the bottom of the product page to load
    wait(browser, WAIT_TIME).until(located((By.CSS_SELECTOR, "div#navFooter")))

    product_name = get_product_name(browser)
    product_data["product_name"] = product_name
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

    amazon_choice_badges = browser.find_elements(By.CSS_SELECTOR, ".ac-badge-rectangle")
    if len(amazon_choice_badges) > 0:
        # sanity check
        only(amazon_choice_badges)
        product_data["amazons_choice"] = True

    # buyboxes are the thing on the right side with the price etc.
    # there might be more than one, e.g. one for new and one for used
    buyboxes = browser.find_elements(By.CSS_SELECTOR, "#buyBoxAccordion")
    if len(buyboxes) > 0:
        # sanity check
        only(buyboxes)
        # use data from the first side box
        box_prefix = "#buyBoxAccordion > div:first-child "
    else:
        box_prefix = ""

    prices = browser.find_elements(
        By.CSS_SELECTOR,
        box_prefix
        + "#corePrice_feature_div .a-price, "
        + box_prefix
        + "#booksHeaderSection span#price, "
        + box_prefix
        + "#usedBuySection div.a-column .offer-price, "
        + box_prefix
        + "#renewedBuyBoxPrice",
    )

    # some of these are not mutually exclusive, so try twice
    # TODO: figure out what's going on
    availabilities = browser.find_elements(
        By.CSS_SELECTOR, box_prefix + "#availability"
    )
    if len(availabilities) == 0:
        availabilities = browser.find_elements(
            By.CSS_SELECTOR,
            box_prefix
            + ".qa-buybox-block .qa-availability-message, "
            + box_prefix
            + "#exports_desktop_outOfStock_buybox_message_feature_div",
        )

    if len(availabilities) == 0:
        # assume it's available unless it says otherwise
        available = True
    else:
        availability = only(availabilities).text
        product_data["availability"] = availability
        available = not (
            availability
            == "Currently unavailable.\nWe don't know when or if this item will be back in stock."
            or availability
            == "Temporarily out of stock.\nWe are working hard to be back in stock as soon as possible."
        )

    undeliverable_messages = browser.find_elements(
        By.CSS_SELECTOR,
        box_prefix
        + "#exports_desktop_undeliverable_buybox_priceInsideBuybox_feature_div",
    )

    if available:
        if len(undeliverable_messages) > 0:
            product_data["availability"] = only(undeliverable_messages).text
            # sometimes there's still a price even if its undeliverable
            # these aren't mutually exclusive so check them seperately
            buybox_prices = browser.find_elements(
                By.CSS_SELECTOR, box_prefix + "#price_inside_buybox"
            )
            main_prices = browser.find_elements(
                By.CSS_SELECTOR, "#corePrice_desktop span.a-price"
            )
            if len(buybox_prices) > 0:
                product_data["current_price"] = get_price(only(buybox_prices))
            elif len(main_prices) > 0:
                product_data["current_price"] = get_price(only(main_prices))
        elif len(prices) == 0:
            # there's a special format for a kindle discount
            kindle_discount_prices = browser.find_elements(
                By.CSS_SELECTOR, box_prefix + "#kindle-price"
            )
            if len(kindle_discount_prices) > 0:
                product_data["kindle_discount"] = True
                # sanity check
                only(kindle_discount_prices)
                product_data["current_price"] = parse_price(
                    only(kindle_discount_prices).text
                )
            else:
                # and another special format if its only available on kindle
                only_kindle_messages = browser.find_elements(
                    By.CSS_SELECTOR, box_prefix + "span.no-kindle-offer-message"
                )
                if len(only_kindle_messages) > 0:
                    only(only_kindle_messages)
                    product_data["current_price"] = only(
                        browser.find_elements(
                            By.CSS_SELECTOR,
                            box_prefix + "span.a-button-selected span.a-color-price",
                        )
                    ).text
                else:
                    # for books etc. with many sellers, a single price won't show
                    # click to look at the sellers
                    only(
                        browser.find_elements(
                            By.CSS_SELECTOR,
                            box_prefix + "a[title='See All Buying Options']",
                        )
                    ).click()

                    # wait for the sellers list
                    wait(browser, WAIT_TIME).until(
                        located((By.CSS_SELECTOR, "#aod-offer-list"))
                    )

                    seller_prices = browser.find_elements(
                        By.CSS_SELECTOR,
                        "#aod-offer-list > div:first-of-type .a-price",
                    )
                    if len(seller_prices) > 0:
                        product_data["current price"] = get_price(only(seller_prices))

                    delivery_widgets = browser.find_elements(
                        By.CSS_SELECTOR,
                        "#aod-offer-list > div:first-of-type #mir-layout-DELIVERY_BLOCK-slot-PRIMARY_DELIVERY_MESSAGE_LARGE span[data-csa-c-type='element']",
                    )

                    if len(delivery_widgets) > 0:
                        delivery_widget = only(delivery_widgets)
                        product_data[
                            "shipping_cost_message"
                        ] = delivery_widget.get_attribute("data-csa-c-delivery-price")
                        product_data["delivery_range"] = delivery_widget.get_attribute(
                            "data-csa-c-delivery-time"
                        )

                    # close the sellers list
                    only(
                        browser.find_elements(By.CSS_SELECTOR, ".aod-close-button")
                    ).click()
                    # TODO: get more information here
        else:
            # if there's two prices, the second price is the unit price
            if len(prices) == 2:
                product_data["current_price"] = get_price(prices[0])
                product_data["unit_price"] = get_price(prices[1])
                # not a separate element so have to extract from the text

                product_data["unit"] = search(
                    r"^\(\n.* \/ ?(.*)\)$",
                    only(
                        browser.find_elements(
                            By.CSS_SELECTOR,
                            box_prefix
                            + "#corePrice_feature_div :not(#taxInclusiveMessage).a-size-small, #corePrice_feature_div :not(#taxInclusiveMessage).a-size-mini, #corePrice_feature_div span[data-a-size='small']:not(#taxInclusiveMessage)",
                        )
                    ).text,
                ).group(1)
            else:
                # sanity check: make sure there's only one price
                product_data["current_price"] = get_price(only(prices))

            shipped_bys = browser.find_elements(
                By.CSS_SELECTOR,
                box_prefix
                + "div[tabular-attribute-name='Ships from'] .tabular-buybox-text-message",
            )
            if len(shipped_bys) > 0:
                product_data["shipped_by"] = only(shipped_bys).text

            shipping_cost_messages = browser.find_elements(
                By.CSS_SELECTOR,
                box_prefix
                + "#price-shipping-message, "
                + box_prefix
                + "#desktop_qualifiedBuyBox #amazonGlobal_feature_div > .a-color-secondary",
            )

            # TODO: parse the shipping cost message to get a number
            if len(shipping_cost_messages) > 0:
                product_data["shipping_cost_message"] = only(
                    shipping_cost_messages
                ).text

            standard_delivery_dates = browser.find_elements(
                By.CSS_SELECTOR,
                box_prefix
                + "#mir-layout-DELIVERY_BLOCK-slot-PRIMARY_DELIVERY_MESSAGE_LARGE .a-text-bold",
            )

            if len(standard_delivery_dates) > 0:
                product_data["standard_delivery_date"] = only(
                    standard_delivery_dates
                ).text

            fastest_delivery_dates = browser.find_elements(
                By.CSS_SELECTOR,
                box_prefix
                + "#mir-layout-DELIVERY_BLOCK-slot-SECONDARY_DELIVERY_MESSAGE_LARGE .a-text-bold",
            )
            if len(fastest_delivery_dates) > 0:
                product_data["fastest_delivery_date"] = only(
                    fastest_delivery_dates
                ).text

            list_prices = browser.find_elements(
                By.CSS_SELECTOR,
                box_prefix
                + "#corePriceDisplay_desktop_feature_div span[data-a-strike='true'], "
                + box_prefix
                + "#print-list-price "
                + box_prefix
                + "span#listPrice",
            )
            if len(list_prices) > 0:
                product_data["list_price"] = get_price(only(list_prices))

            prime_prices = browser.find_elements(
                By.CSS_SELECTOR, box_prefix + "#pep-signup-link .a-size-base"
            )
            if len(prime_prices) > 0:
                product_data["prime_price"] = get_price(only(prime_prices))

            #this checks for subscription availability on subcription only products
            subscription_legal_text = browser.find_elements(
                By.CSS_SELECTOR, "#sndbox-legalText"
            )
            if len(subscription_legal_text) > 0 and "Automatically renews" in only(subscription_legal_text).text:
                product_data["subscription"] = True

            #this checks for subscription availability on subcription as an option products
            subscription_price = browser.find_elements(
                By.CSS_SELECTOR, "span[id='subscriptionPrice']"
            )
            if len(subscription_price) > 0 and "$" in only(subscription_price).text:
                product_data["subscription_price"] = True

            return_policy_text = browser.find_elements(
                    By.CSS_SELECTOR, "#productSupportAndReturnPolicy-return-policy-anchor-text"
            )

            if len(return_policy_text) > 0:
                product_data["return_policy"] = only(return_policy_text).text
            else:
                amazon_renewed_check = browser.find_elements(
                    By.CSS_SELECTOR, "#bylineInfo_feature_div .a-link-normal"
                )
                if len(amazon_renewed_check) > 0 and only(amazon_renewed_check).text == "Visit the Amazon Renewed Store":
                    product_data["return_policy"] = "Amazon Renewed"

    category_navigation_widget = browser.find_elements(By.CSS_SELECTOR, "#wayfinding-breadcrumbs_feature_div")

    if len(category_navigation_widget) > 0:
        category_links = category_navigation_widget[0].find_elements(
            By.CSS_SELECTOR, "a[class='a-link-normal a-color-tertiary']"
        )

        for i, link in enumerate(category_links[:5]):
            if link and link.text:
                product_data[f"sub_category_{i}"] = link.text.replace("\n", "").replace(" ", "")
            else:
                product_data[f"sub_category_{i}"] = None

    average_ratings = browser.find_elements(
        By.CSS_SELECTOR,
        ".cr-widget-TitleRatingsHistogram span[data-hook='rating-out-of-text']",
    )
    if len(average_ratings) > 0:
        # TODO: sanity check verify no ratings
        product_data["average_rating"] = float(
            search(r"^(.*) out of 5$", only(average_ratings).text).group(1)
        )
        product_data["number_of_ratings"] = int(
            remove_commas(
                search(
                    r"^(.*) global ratings?$",
                    only(
                        browser.find_elements(
                            By.CSS_SELECTOR,
                            ".cr-widget-TitleRatingsHistogram div[data-hook='total-review-count']",
                        )
                    ).text,
                ).group(1)
            )
        )
        histogram_rows = get_histogram_rows(browser)
        if len(histogram_rows) != 5:
            raise "Unexpected number of histogram rows!"

        product_data["five_star_percentage"] = get_star_percentage(
            get_histogram_rows(browser)[0]
        )
        product_data["four_star_percentage"] = get_star_percentage(
            get_histogram_rows(browser)[1]
        )
        product_data["three_star_percentage"] = get_star_percentage(
            get_histogram_rows(browser)[2]
        )
        product_data["two_star_percentage"] = get_star_percentage(
            get_histogram_rows(browser)[3]
        )
        product_data["one_star_percentage"] = get_star_percentage(
            get_histogram_rows(browser)[4]
        )
    return product_name, product_data


# query = "fire hd 10 tablet"
# browser = new_browser(USER_AGENT_LIST[0])
# department = "All Departments"
def scrape_products(
    browser_box,
    search_results_data,
    product_results_folder,
    user_agents,
    user_agent_index=0,
):
    browser = new_browser(user_agents[user_agent_index])
    browser_box.append(browser)

    # no previous product, so starts empty
    old_product_name = ""
    for (groups, search_results_chunk) in search_results_data.groupby(["search_term"]):
        print(groups)
        print(search_results_chunk.loc[:, "url"])
        product_rows = []
        for product_url in search_results_chunk.loc[0:2, "url"]:
            print("Reading product page " + product_url)

            try:
                old_product_name, product_data = try_parse_product(
                    browser, product_url, old_product_name
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
                    old_product_name, product_data = try_parse_product(
                        browser, product_url, old_product_name
                    )
                else:
                    raise an_error
            product_rows.append(product_data)

        dicts_to_dataframe(product_rows).to_csv(
            path.join(
                # search term is the only group
                product_results_folder, groups[0] + ".csv"
            )
        )

    return user_agent_index
