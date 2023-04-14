from os import path, listdir
from pandas import DataFrame, read_csv, concat
from re import search
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.expected_conditions import presence_of_element_located as located
from selenium.webdriver.support.expected_conditions import presence_of_all_elements_located as all_located
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.wait import WebDriverWait as wait

WAIT_TIME = 20

# throw an error if there isn't one and only one result
# important safety measure for CSS selectors
def only(list):
    count = len(list)
    if count != 1:
        raise IndexError(count)
    return list[0]

# e.g. 1,000 -> 1000
def remove_commas(a_string):
    return a_string.replace(',', '')

def get_price(price_widget):
    # some prices have separate dollar and cent parts
    dollar_parts = price_widget.find_elements(By.CSS_SELECTOR, ".a-price-whole")
    if len(dollar_parts) > 0:
        # dollars
        return int(
            remove_commas(only(price_widget.find_elements(
                By.CSS_SELECTOR,
                ".a-price-whole"
            )).text)
        # cents
        ) + int(
            remove_commas(only(price_widget.find_elements(
                By.CSS_SELECTOR,
                ".a-price-fraction"
            )).text)
        ) / 100
    else:
        # others are all together
        return parse_price(price_widget.text)

def parse_price(price_string):
    # ignore the dollar sign in front
    return float(remove_commas(price_string[1:]))

def get_star_percentage(histogram_row):
    return only(histogram_row.find_elements(By.CSS_SELECTOR, ".a-text-right > .a-size-base")).text

def new_browser(
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Safari/537.36"
):
    options = Options()
    # add headless to avoid the visual display and speed things up
    # options.add_argument("-headless")
    options.set_preference("general.useragent.override", user_agent)
    # this helps pages load faster I guess?
    options.set_capability("pageLoadStrategy", "eager")
    
    browser = webdriver.Firefox(options = options)
    # selenium sputters when scripts run too long so set a timeout
    browser.set_script_timeout(WAIT_TIME)
    return browser

def try_run_search(browser, department, query):
    department_menus = browser.find_elements(
        By.CSS_SELECTOR,
        "#searchDropdownBox"
    )

    if len(department_menus) == 0:
        browser.refresh()
        wait(browser, WAIT_TIME).until(located((
            By.CSS_SELECTOR,
            # one for each version of the main screen
            "#twotabsearchtextbox, #nav-bb-search"
        )))
        return try_run_search(browser, department, query)
    
    department_menu = only(department_menus)
    print(query + ":")
    department_selector = Select(department_menu)
    if department != department_selector.first_selected_option.text:
        # we need to mess with the drop down to activate it I guess
        department_menu.send_keys(Keys.DOWN)
        department_selector.select_by_visible_text(department)
        
    search_bar = only(browser.find_elements(
        By.CSS_SELECTOR,
        "#twotabsearchtextbox"
    ))
    
    search_bar.clear()
    search_bar.send_keys(query)
    search_bar.send_keys(Keys.RETURN)
    # don't know what the placeholder is for but it seems to load after the search results?
    wait(browser, WAIT_TIME).until(located((By.CSS_SELECTOR, "div.s-result-list-placeholder")))

    return [parse_search_result(browser, query, index) for index in range(len(browser.find_elements(
        By.CSS_SELECTOR,
        "div.s-main-slot.s-result-list > div[data-component-type='s-search-result']"
    )))]

def get_product_name(browser):
    return only(browser.find_elements(
        By.CSS_SELECTOR,
        "span#productTitle, span.qa-title-text"
    )).text

def parse_search_result(browser, query, index):
    print("Parsing search result #{index}".format(index = index))
    product_data = {"search_term": query, "rank": index + 1}
    search_result = browser.find_elements(
        By.CSS_SELECTOR,
        "div.s-main-slot.s-result-list > div[data-component-type='s-search-result']"
    )[index]

    sponsored_tags = search_result.find_elements(
        By.CSS_SELECTOR,
        ".puis-label-popover-default"
    )
    if len(sponsored_tags) > 0:
        # sanity check
        only(sponsored_tags)
        product_data["ad"] = True
    
    product_data["url"] = only(search_result.find_elements(
        By.CSS_SELECTOR,
        # a link in a heading
        "h2 a"
    )).get_attribute("href")

    return product_data

def get_choice_sets(browser):
    return browser.find_elements(
        By.CSS_SELECTOR,
        "#twister-plus-inline-twister > div.inline-twister-row"
    )

def has_partial_buyboxes(browser):
    return len(browser.find_elements(By.CSS_SELECTOR, "#partialStateBuybox")) > 0
    
# TODO: read the department from a csv instead
# department = "Books"
def download_data(
        browser,
        queries_file,
        search_results_folder,
        department = "All Departments"
    ):

    completed_queries = set((
        path.splitext(filename)[0] for filename in listdir(search_results_folder)
    ))

    browser.get("https://www.amazon.com/")
    wait(browser, WAIT_TIME).until(located((
        By.CSS_SELECTOR,
        # one for each version of the main screen
        "#twotabsearchtextbox, #nav-bb-search"
    )))

    query_data = read_csv(queries_file)

    # query = "chemistry textbook"
    for (category, query) in zip(query_data.loc[:, "category"], query_data.loc[:, "query"]):
        if query in completed_queries:
            continue

        product_rows = try_run_search(browser, department, query)
            
        # no previous product, so starts empty
        old_product_name = ""
        for (index, product_data) in enumerate(product_rows[0:2]):
            print("Reading product page #{index}".format(index = index))
            browser.get(product_data["url"])

            # wait for a new product
            wait(browser, WAIT_TIME).until(
                lambda browser : get_product_name(browser) != 
                    old_product_name
            )

            product_name = get_product_name(browser)
            product_data["product_name"] = product_name
            old_product_name = product_name

            if has_partial_buyboxes(browser):
                # make all selections
                for choice_set_index in range(len(get_choice_sets(browser))):
                    get_choice_sets(browser)[choice_set_index].find_elements(
                        By.CSS_SELECTOR,
                        "ul > li.a-declarative"
                    )[0].click()

                # wait for the buybox to update
                wait(browser, WAIT_TIME).until(
                    lambda browser : not(has_partial_buyboxes(browser))
                )

            amazon_choice_badges = browser.find_elements(
                By.CSS_SELECTOR,
                ".ac-badge-rectangle"
            )
            if len(amazon_choice_badges) > 0:
                # sanity check
                only(amazon_choice_badges)
                product_data["amazons_choice"] = True
            
            sideboxes = browser.find_elements(
                By.CSS_SELECTOR,
                "#buyBoxAccordion"
            )
            if len(sideboxes) > 0:
                # sanity check
                only(sideboxes)
                # use data from the first side box
                box_prefix = "#buyBoxAccordion > div:first-child "
            else:
                box_prefix = ""

            prices = browser.find_elements(
                By.CSS_SELECTOR,
                box_prefix + "#corePrice_feature_div .a-price, " + box_prefix + "#booksHeaderSection span#price, " + box_prefix + "#usedBuySection div.a-column .offer-price"
            )

            availabilities = browser.find_elements(
                By.CSS_SELECTOR,
                box_prefix + "#availability, " + box_prefix + ".qa-buybox-block .qa-availability-message"
            )
            
            if len(availabilities) == 0:
                # assume it's available unless it says otherwise
                available = True
            else:
                availability = only(availabilities).text
                product_data["availability"] = availability
                available = not(
                    availability == "Currently unavailable.\nWe don't know when or if this item will be back in stock." or 
                    availability == "Temporarily out of stock.\nWe are working hard to be back in stock as soon as possible."
                )

            undeliverable_messages = browser.find_elements(
                By.CSS_SELECTOR,
                box_prefix + "#exports_desktop_undeliverable_buybox_priceInsideBuybox_feature_div"
            )

            if available:
                if len(undeliverable_messages) > 0:
                    product_data["availability"] = only(undeliverable_messages).text
                    # sometimes there's still a price even if its undeliverable
                    side_prices = browser.find_elements(
                        By.CSS_SELECTOR,
                        box_prefix + "#price_inside_buybox"
                    )
                    main_prices = browser.find_elements(
                        By.CSS_SELECTOR,
                        "#corePrice_desktop span.a-price"
                    )
                    if len(side_prices) > 0:
                        product_data["current_price"] = get_price(only(side_prices))
                    elif len(main_prices) > 0:
                        product_data["current_price"] = get_price(only(main_prices))
                elif len(prices) == 0:
                    # for books etc. with many sellers, a single price won't show
                    # click to look at the sellers
                    only(browser.find_elements(
                        By.CSS_SELECTOR,
                        box_prefix + "a[title='See All Buying Options']"
                    )).click()

                    # wait for the sellers list
                    wait(browser, WAIT_TIME).until(located((
                        By.CSS_SELECTOR,
                        "#aod-offer-list"
                    )))

                    seller_prices = browser.find_elements(
                        By.CSS_SELECTOR,
                        "#aod-offer-list > div:first-of-type .a-price"
                    )
                    if len(seller_prices) > 0:
                        product_data["current price"] = get_price(only(seller_prices))
                    
                    delivery_widgets = browser.find_elements(
                        By.CSS_SELECTOR,
                        "#aod-offer-list > div:first-of-type span[data-csa-c-type='element']"
                    )

                    if len(delivery_widgets) > 0:

                        delivery_widget = only(delivery_widgets)
                        product_data["shipping_cost_message"] = delivery_widget.get_attribute(
                            "data-csa-c-delivery-price"
                        )
                        product_data["delivery_range"] = delivery_widget.get_attribute(
                            "data-csa-c-delivery-time"
                        )

                    # close the sellers list
                    only(browser.find_elements(
                        By.CSS_SELECTOR,
                        ".aod-close-button"
                    )).click()
                    # TODO: get more information here
                else:
                    # if there's two prices, the second price is the unit price
                    if len(prices) == 2:
                        product_data["current_price"] = get_price(prices[0])
                        product_data["unit_price"] = get_price(prices[1])
                        # not a separate element so have to extract from the text
                        
                        product_data["unit"] = search(r"^\(\n.* \/ (.*)\)$", only(
                            browser.find_elements(
                                By.CSS_SELECTOR,
                                box_prefix + "#corePrice_feature_div :not(#taxInclusiveMessage).a-size-small, #corePrice_feature_div :not(#taxInclusiveMessage).a-size-mini, #corePrice_feature_div span[data-a-size='small']:not(#taxInclusiveMessage)"
                            )
                        ).text).group(1)
                    else:
                        # sanity check: make sure there's only one price
                        product_data["current_price"] = get_price(only(prices))
                    
                    shipped_bys = browser.find_elements(
                        By.CSS_SELECTOR,
                        box_prefix + "div[tabular-attribute-name='Ships from'] .tabular-buybox-text-message"
                    )
                    if len(shipped_bys) > 0:
                        product_data["shipped_by"] = only(shipped_bys).text
                        
                    shipping_cost_messages = browser.find_elements(
                        By.CSS_SELECTOR,
                        box_prefix + "#price-shipping-message, " +
                        box_prefix + "#desktop_qualifiedBuyBox #amazonGlobal_feature_div > .a-color-secondary"
                    )
                    
                    # TODO: parse the shipping cost message to get a number
                    if len(shipping_cost_messages) > 0:
                        product_data["shipping_cost_message"] = only(shipping_cost_messages).text
            
                    standard_delivery_dates = browser.find_elements(
                        By.CSS_SELECTOR,
                        box_prefix + "#mir-layout-DELIVERY_BLOCK-slot-PRIMARY_DELIVERY_MESSAGE_LARGE .a-text-bold"
                    )

                    if len(standard_delivery_dates) > 0:         
                        product_data["standard_delivery_date"] = only(standard_delivery_dates).text
                    
                    fastest_delivery_dates = browser.find_elements(
                        By.CSS_SELECTOR,
                        box_prefix + "#mir-layout-DELIVERY_BLOCK-slot-SECONDARY_DELIVERY_MESSAGE_LARGE .a-text-bold"
                    )
                    if len(fastest_delivery_dates) > 0:
                        product_data["fastest_delivery_date"] = only(fastest_delivery_dates).text
                        
                    list_prices = browser.find_elements(By.CSS_SELECTOR, box_prefix + "#corePriceDisplay_desktop_feature_div span[data-a-strike='true']")
                    if len(list_prices) > 0:
                        product_data["list_price"] = get_price(only(list_prices))
                    
                    prime_prices = browser.find_elements(
                        By.CSS_SELECTOR,
                        box_prefix + "#pep-signup-link .a-size-base"
                    )
                    if len(prime_prices) > 0:
                        product_data["prime_price"] = get_price(only(prime_prices))
            
            average_ratings = browser.find_elements(
                By.CSS_SELECTOR,
                ".cr-widget-TitleRatingsHistogram span[data-hook='rating-out-of-text']"
            )
            if len(average_ratings) > 0:
                # TODO: sanity check verify no ratings
                product_data["average_rating"] = float(
                    search(
                        r"^(.*) out of 5$",
                        only(average_ratings).text
                    ).group(1)
                )
                product_data["number_of_ratings"] = int(remove_commas(search(
                    r"^(.*) global ratings?$",
                    only(browser.find_elements(
                        By.CSS_SELECTOR,
                        ".cr-widget-TitleRatingsHistogram div[data-hook='total-review-count']"
                    )).text
                ).group(1)))
                histogram_rows = browser.find_elements(
                    By.CSS_SELECTOR,
                    ".cr-widget-TitleRatingsHistogram .a-histogram-row"
                )
                if len(histogram_rows) != 5:
                    raise "Unexpected number of histogram rows!"
                
                product_data["five_star_percentage"] = get_star_percentage(
                    histogram_rows[0]
                )
                product_data["four_star_percentage"] = get_star_percentage(
                    histogram_rows[1]
                )
                product_data["three_star_percentage"] = get_star_percentage(
                    histogram_rows[2]
                )
                product_data["two_star_percentage"] = get_star_percentage(
                    histogram_rows[3])
                product_data["one_star_percentage"] = get_star_percentage(
                    histogram_rows[4]
                )

        # possible there's no results
        if len(product_rows) > 0:
            concat((DataFrame(product_data, [0]) for product_data in product_rows)).to_csv(path.join(search_results_folder, query + ".csv"), index = False)

        # TODO:
        # number of option boxes
        # name of the selected option box
        # number of sidebar boxes
        # name of the selected sidebar box
        # number of sellers (for items with multiple sellers)
        # coupons
        # categories
        # seller name
        # whether eligable for refund
        # whether limited time deal
        # whether small business icon
        # whether bundles available
        # whether subscription available
