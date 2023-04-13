from os import path, listdir
from pandas import DataFrame, read_csv, concat
from re import search
from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException
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

def get_search_results(search_browser):
    return search_browser.find_elements(
        By.CSS_SELECTOR,
        "div[data-component-type='s-search-result']"
    )

def get_product_name(product_browser):
    return only(product_browser.find_elements(
        By.CSS_SELECTOR,
        "span#productTitle"
    )).text

# TODO: read the department from a csv instead
# department = "Books"
def download_data(search_browser, product_browser, queries_file, search_results_folder, department = "All Departments"):

    completed_queries = set((
        path.splitext(filename)[0] for filename in listdir(search_results_folder)
    ))

    search_browser.get("https://www.amazon.com/")
    wait(search_browser, WAIT_TIME).until(located((
        By.CSS_SELECTOR,
        # one for each version of the main screen
        "#twotabsearchtextbox, #nav-bb-search"
    )))

    query_data = read_csv(queries_file)
    
    # query = "chemistry textbook"
    for (category, query) in zip(query_data.loc[:, "category"], query_data.loc[:, "query"]):
        if query in completed_queries:
            continue
        print(query + ":")
        department_menus = search_browser.find_elements(
            By.CSS_SELECTOR,
            "#searchDropdownBox"
        )
        if len(department_menus) == 0:
            # TODO: figure out why this is happening
            print("Cannot select department, try again")
            break
        department_menu = only(department_menus)
        department_selector = Select(department_menu)
        if department != department_selector.first_selected_option.text:
            # we need to mess with the drop down to activate it I guess
            department_menu.send_keys(Keys.DOWN)
            department_selector.select_by_visible_text(department)
            
        search_bar = only(search_browser.find_elements(
            By.CSS_SELECTOR,
            "#twotabsearchtextbox"
        ))
        
        search_bar.clear()
        search_bar.send_keys(query)
        search_bar.send_keys(Keys.RETURN)
        # wait for all the product links to load
        wait(search_browser, WAIT_TIME).until(all_located((By.CSS_SELECTOR, "h2 a")))

        product_rows = []
        # no previous product, so starts empty
        old_product_name = ""
        successful = True
        # index = 0
        # search_result = get_search_results(search_browser)[index]
        for (index, search_result) in enumerate(get_search_results(search_browser)):
            try:
                product_data = {"search_term": query, "rank": index + 1}

                sponsored_tags = search_result.find_elements(
                    By.CLASS_NAME,
                    "puis-label-popover-default"
                )
                if len(sponsored_tags) > 0:
                    # sanity check
                    only(sponsored_tags)
                    product_data["ad"] = True
                
                product_url = only(search_result.find_elements(
                    By.CSS_SELECTOR,
                    # a link in a heading
                    "h2 a"
                )).get_attribute("href")

                print("#{index}".format(index = index))

                product_data["url"] = product_url
                product_browser.get(product_url)

                # wait for a new product
                wait(product_browser, WAIT_TIME).until(
                    lambda product_browser : get_product_name(product_browser) != 
                        old_product_name
                )

                product_name = get_product_name(product_browser)
                product_data["product_name"] = product_name
                old_product_name = product_name

                # make a required choice
                required_choices = product_browser.find_elements(
                    By.CSS_SELECTOR,
                    "#twister-plus-inline-twister ul > li.a-declarative"
                )
                if len(required_choices) > 0:
                    # click the first choice I guess
                    required_choices[0].click()
                    wait(product_browser, WAIT_TIME).until(located((
                        By.CSS_SELECTOR,
                        ".text-swatch-button-with-slots.a-button-selected, .image-swatch-button.a-button-selected"
                    )))

                amazon_choice_badges = product_browser.find_elements(
                    By.CSS_SELECTOR,
                    ".ac-badge-rectangle"
                )
                if len(amazon_choice_badges) > 0:
                    # sanity check
                    only(amazon_choice_badges)
                    product_data["amazons_choice"] = True
                
                sideboxes = product_browser.find_elements(
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

                prices = product_browser.find_elements(
                    By.CSS_SELECTOR,
                    box_prefix + "#corePrice_feature_div .a-price, " + 
                    box_prefix + "#booksHeaderSection span#price"
                )

                availabilities = product_browser.find_elements(
                    By.CSS_SELECTOR,
                    box_prefix + "#availability"
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

                undeliverable_messages = product_browser.find_elements(
                    By.CSS_SELECTOR,
                    box_prefix + "#exports_desktop_undeliverable_buybox_priceInsideBuybox_feature_div"
                )

                if available:
                    if len(undeliverable_messages) > 0:
                        product_data["availability"] = only(undeliverable_messages).text
                        # sometimes there's still a price even if its undeliverable
                        side_prices = product_browser.find_elements(
                            By.CSS_SELECTOR,
                            box_prefix + "#price_inside_buybox"
                        )
                        main_prices = product_browser.find_elements(
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
                        only(product_browser.find_elements(
                            By.CSS_SELECTOR,
                            box_prefix + "a[title='See All Buying Options']"
                        )).click()

                        # wait for the sellers list
                        wait(product_browser, WAIT_TIME).until(located((
                            By.CSS_SELECTOR,
                            "#aod-offer-list"
                        )))

                        seller_prices = product_browser.find_elements(
                            By.CSS_SELECTOR,
                            "#aod-offer-list > div:first-of-type .a-price"
                        )
                        if len(seller_prices) > 0:
                            product_data["current price"] = get_price(only(seller_prices))
                        
                        delivery_widgets = product_browser.find_elements(
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
                        only(product_browser.find_elements(
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
                                product_browser.find_elements(
                                    By.CSS_SELECTOR,
                                    box_prefix + "#corePrice_feature_div :not(#taxInclusiveMessage).a-size-small, #corePrice_feature_div :not(#taxInclusiveMessage).a-size-mini, #corePrice_feature_div span[data-a-size='small']:not(#taxInclusiveMessage)"
                                )
                            ).text).group(1)
                        else:
                            # sanity check: make sure there's only one price
                            product_data["current_price"] = get_price(only(prices))

                        # all these should available if it's in stock
                        product_data["shipped_by"] = only(product_browser.find_elements(
                            By.CSS_SELECTOR,
                            box_prefix + "div[tabular-attribute-name='Ships from'] .tabular-buybox-text-message"
                        )).text
                        product_data["seller_name"] = only(product_browser.find_elements(
                            By.CSS_SELECTOR,
                            box_prefix + "div[tabular-attribute-name='Sold by'] .tabular-buybox-text-message"
                        )).text
                        shipping_promotions = product_browser.find_elements(
                            By.CSS_SELECTOR,
                            box_prefix + "#price-shipping-message"
                        )
                        # TODO: parse the shipping cost message to get a number
                        if len(shipping_promotions) > 0:
                            product_data["shipping_cost_message"] = only(shipping_promotions).text
                        else:
                            product_data["shipping_cost_message"] = only(product_browser.find_elements(
                                By.CSS_SELECTOR,
                                box_prefix + "#desktop_qualifiedBuyBox #amazonGlobal_feature_div > .a-color-secondary"
                            )).text
                
                        standard_delivery_dates = product_browser.find_elements(
                            By.CSS_SELECTOR,
                            box_prefix + "#mir-layout-DELIVERY_BLOCK-slot-PRIMARY_DELIVERY_MESSAGE_LARGE .a-text-bold"
                        )

                        if len(standard_delivery_dates) > 0:         
                            product_data["standard_delivery_date"] = only(standard_delivery_dates).text
                        
                        fastest_delivery_dates = product_browser.find_elements(
                            By.CSS_SELECTOR,
                            box_prefix + "#mir-layout-DELIVERY_BLOCK-slot-SECONDARY_DELIVERY_MESSAGE_LARGE .a-text-bold"
                        )
                        if len(fastest_delivery_dates) > 0:
                            product_data["fastest_delivery_date"] = only(fastest_delivery_dates).text
                            
                        list_prices = product_browser.find_elements(By.CSS_SELECTOR, box_prefix + "#corePriceDisplay_desktop_feature_div span[data-a-strike='true']")
                        if len(list_prices) > 0:
                            product_data["list_price"] = get_price(only(list_prices))
                        
                        prime_prices = product_browser.find_elements(
                            By.CSS_SELECTOR,
                            box_prefix + "#pep-signup-link .a-size-base"
                        )
                        if len(prime_prices) > 0:
                            product_data["prime_price"] = get_price(only(prime_prices))
                
                average_ratings = product_browser.find_elements(
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
                        only(product_browser.find_elements(
                            By.CSS_SELECTOR,
                            ".cr-widget-TitleRatingsHistogram div[data-hook='total-review-count']"
                        )).text
                    ).group(1)))
                    histogram_rows = product_browser.find_elements(
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

                product_rows.append(DataFrame(product_data, [0]))
            except StaleElementReferenceException:
                # TODO: figure out why this is happening
                print("Page refreshed during the search; try again")
                successful = False
                break

        # possible there's no results
        if successful and len(product_rows) > 0:
            concat(product_rows).to_csv(path.join(search_results_folder, query + ".csv"), index = False)

        # TODO:
        # number of option boxes
        # name of the selected option box
        # number of sidebar boxes
        # name of the selected sidebar box
        # number of sellers (for items with multiple sellers)
        # coupons
        # categories
        # whether eligable for refund
        # whether limited time deal
        # whether small business icon
        # whether bundles available
        # whether subscription available
