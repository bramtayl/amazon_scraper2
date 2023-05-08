from os import path
from pandas import concat, DataFrame
import re
from src.utilities import get_filenames, only, read_html
import webbrowser

def find_products(product_pages_folder, selector, number_of_products = 5):
    found = 0
    for product_filename in get_filenames(product_pages_folder):
        product_file = path.join(product_pages_folder, product_filename + ".html")
        product_page = read_html(product_file)
        if len(product_page.select(selector)) > 0:
            webbrowser.open(product_file)
            found = found + 1
            if found == number_of_products:
                break

# e.g. 1,000 -> 1000
def remove_commas(a_string):
    return a_string.replace(",", "")

def get_price(price_widget):
    return float(remove_commas(re.match(r"^\$(.*)$", price_widget.text.strip()).group(1)))

def get_star_percentage(histogram_row):
    return only(histogram_row.select(".a-text-right > .a-size-base")).text.strip()

class NotFiveRows(Exception):
    pass

class NotNoReviews(Exception):
    pass

class NotUnsupported(Exception):
    pass

class NotReviewSummary(Exception):
    pass

class NotOneOrTwoPrices(Exception):
    pass

class NoBuyBox(Exception):
    pass

class UnrecognizedBuybox(Exception):
    pass

def parse_product_page(product_pages_folder, product_filename, product_type, product_page):

    average_rating = None
    number_of_ratings = None
    one_star_percentage = None
    two_star_percentage = None
    three_star_percentage = None
    four_star_percentage = None
    five_star_percentage = None

    ratings_widgets = product_page.select("span.cr-widget-TitleRatingsHistogram")
    if len(ratings_widgets) > 0:
        ratings_widget = only(ratings_widgets)
        average_ratings_widgets = ratings_widget.select("span[data-hook='rating-out-of-text']")
        if len(average_ratings_widgets) > 0:
            average_rating = float(
                re.search(
                    r"^(.*) out of 5$", only(average_ratings_widgets).text.strip()
                ).group(1)
            )
            number_of_ratings = int(
                remove_commas(
                    re.search(
                        r"^(.*) global ratings?$",
                        only(
                            ratings_widget.select(
                                "[data-hook='total-review-count']", 
                            )
                        ).text.strip(),
                    ).group(1)
                )
            )
            histogram_rows = ratings_widget.select(
                ".a-histogram-row"
            )
            if len(histogram_rows) != 5:
                raise NotFiveRows()

            five_star_percentage = get_star_percentage(
                histogram_rows[0]
            )
            four_star_percentage = get_star_percentage(
                histogram_rows[1]
            )
            three_star_percentage = get_star_percentage(
                histogram_rows[2]
            )
            two_star_percentage = get_star_percentage(
                histogram_rows[3]
            )
            one_star_percentage = get_star_percentage(
                histogram_rows[4]
            )

    hidden_price_widgets = product_page.select("a[href='/forum/where%20is%20the%20price']")
    if len(hidden_price_widgets) > 0:
        only(hidden_price_widgets)
        hidden_prices = True
    else:
        hidden_prices = False

    accordion_rows = product_page.select("#buyBoxAccordion div[id*='AccordionRow']")
    if len(accordion_rows) > 0:
        buybox = accordion_rows[0]
    else:
        buybox = only(product_page.select("div[data-csa-c-content-id='desktop_buybox_group_1']"))

    out_of_stock_widgets = buybox.select("div#outOfStock")
    if len(out_of_stock_widgets) > 0:
        only(out_of_stock_widgets)
        out_of_stock = True
    else:
        out_of_stock = False
    
    undeliverable_widgets = buybox.select("div#exports_desktop_undeliverable_buybox") 
    if len(undeliverable_widgets) > 0:
        only(undeliverable_widgets)
        undeliverable = True
    else:
        undeliverable = False
    
    price = None
    unit_price = None
    unit_text = ""
    
    offer_price_widgets = buybox.select("div.a-grid-center span.offer-price")
    if len(offer_price_widgets) > 0:
        price = get_price(only(offer_price_widgets))

    renewed_price_widgets = buybox.select("span#renewedBuyBoxPrice")
    if len(renewed_price_widgets) > 0:
        price = get_price(only(renewed_price_widgets))

    price_pair_widgets = buybox.select("div#corePrice_feature_div")
    if len(price_pair_widgets) > 0:
        price_pair_widget = only(price_pair_widgets)
        unit_text = price_pair_widget.text.strip()
        price_widgets = price_pair_widget.select("span.a-offscreen")
        if len(price_widgets) == 0:
            pass
        elif len(price_widgets) == 1:
            price = get_price(price_widgets[0])
        elif len(price_widgets) == 2:
            price = get_price(price_widgets[0])
            unit_price = get_price(price_widgets[0])
        else:
            raise NotOneOrTwoPrices()

    availability_widgets = buybox.select("div#availability")
    if len(availability_widgets) > 0:
        availability = only(availability_widgets).text.strip()
    else:
        availability = ""

    non_returnable_widgets = product_page.select("div#dsvReturnPolicyMessage_feature_div")
    if len(non_returnable_widgets) > 0:
        returns = only(non_returnable_widgets).text.strip()
    else:
        returns_widgets = buybox.select("a#creturns-policy-anchor-text")
        if len(returns_widgets) > 0:
            returns = only(returns_widgets).text.strip()
        else:
            returns = ""

    primary_delivery_widgets = buybox.select("div#mir-layout-DELIVERY_BLOCK-slot-PRIMARY_DELIVERY_MESSAGE_LARGE span.a-text-bold")
    if len(primary_delivery_widgets):
        primary_delivery_date = only(primary_delivery_widgets).text.strip()
    else:
        primary_delivery_date = ""

    secondary_delivery_widgets = buybox.select("div#mir-layout-DELIVERY_BLOCK-slot-SECONDARY_DELIVERY_MESSAGE_LARGE span.a-text-bold")
    if len(secondary_delivery_widgets) > 0:
        secondary_delivery_date = only(secondary_delivery_widgets).text.strip()
    else:
        secondary_delivery_date = ""

    ships_from_widgets = buybox.select("div.tabular-buybox-text[tabular-attribute-name='Ships from']")
    if len(ships_from_widgets) > 0:
        ships_from = only(ships_from_widgets).text.strip()
    else:
        ships_from = ""

    sold_by_widgets = buybox.select("div.tabular-buybox-text[tabular-attribute-name='Sold by']")
    if len(sold_by_widgets) > 0:
        sold_by = only(sold_by_widgets).text.strip()
    else:
        sold_by = ""

    fakespot_widgets = product_page.select("div.fakespot-main-grade-box-wrapper")
    if len(fakespot_widgets) > 0:
        fakespot_grade = only(product_page.select("div#fs-letter-grade-box")).text.strip()
    else:
        fakespot_grade = ""

    category_widgets = product_page.select("div#wayfinding-breadcrumbs_feature_div ul.a-unordered-list li:last-of-type")
    if len(category_widgets) > 0:
        category = only(category_widgets).text.strip()
    else:
        category = ""

    new_seller_widgets = product_page.select("div#fakespot-badge")
    if len(new_seller_widgets) > 0:
        only(new_seller_widgets)
        new_seller = True
    else:
        new_seller = False

    climate_friendly_widgets = product_page.select("div#climatePledgeFriendly")
    if len(climate_friendly_widgets) > 0:
        only(climate_friendly_widgets)
        climate_friendly = True
    else:
        climate_friendly = False

    subscription_widgets = product_page.select("div#snsAccordionRowMiddle")
    if len(subscription_widgets):
        subscription_available = True
    else:
        subscription_available = False

    choose_seller_widgets = product_page.select("a[title='See All Buying Options']")
    if len(choose_seller_widgets) > 0:
        only(choose_seller_widgets)
        sellers_page = read_html(path.join(product_pages_folder, product_filename + "-sellers.html"))
        # TODO: all the stuff here

    amazons_choice_widgets = product_page.select("acBadge_feature_div")
    if len(amazons_choice_widgets) > 0:
        only(amazons_choice_widgets)
        amazons_choice = True
    else:
        amazons_choice = False

    return DataFrame({
        "product_filename": product_filename,
        "average_rating": average_rating,
        "number_of_ratings": number_of_ratings,
        "one_star_percentage": one_star_percentage,
        "two_star_percentage": two_star_percentage,
        "three_star_percentage": three_star_percentage,
        "four_star_percentage": four_star_percentage,
        "five_star_percentage": five_star_percentage,
        "price": price,
        "unit_price": unit_price,
        "fakespot_grade": fakespot_grade,
        "returns": returns,
        "primary_delivery_date": primary_delivery_date,
        "secondary_delivery_date": secondary_delivery_date,
        "ships_from": ships_from,
        "sold_by": sold_by,
        "category": category,
        "new_seller": new_seller,
        "climate_friendly": climate_friendly,
        "subscription_available": subscription_available,
        "out_of_stock": out_of_stock,
        "undeliverable": undeliverable,
        "hidden_prices": hidden_prices,
        "availability": availability,
        "product_type": product_type,
        "unit_text": unit_text
    }, index = [0])
        

# product_id = "380"
def parse_product_pages(product_pages_folder):
    product_rows = []
    for product_filename in get_filenames(product_pages_folder):
        print(product_filename)
        # all digits
        if not(re.match(r"^.*\-sellers$", product_filename) is None):
            continue
        
        product_page = read_html(path.join(product_pages_folder, product_filename + ".html"))

        try:
            unsupported_browser_widgets = product_page.select("h2.heading.title")
            if len(unsupported_browser_widgets) > 0:
                if only(unsupported_browser_widgets).text.strip() != "Your browser is not supported":
                    raise NotUnsupported()
                continue

            consider_alternative_widgets = product_page.select("div#percolate-ui-lpo_div")
            if len(consider_alternative_widgets) > 0:
                only(consider_alternative_widgets)
                continue
            
            page_type_widgets = product_page.select("div#dp")
            if len(page_type_widgets) == 0:
                continue
            
            page_type = only(page_type_widgets)["class"][0]
            if page_type == "book" or page_type == "ebooks" or page_type == "digitaltextfeeds" or page_type == "digital_software" or page_type == "device-type-desktop" or page_type == "audible" or page_type == "swa_physical":
                continue
            
            product_rows.append(parse_product_page(product_pages_folder, product_filename, page_type, product_page))

            # undeliverable_messages = product_page.select(
            #     By.CSS_SELECTOR,
            #     box_prefix
            #     + "#exports_desktop_undeliverable_buybox_priceInsideBuybox_feature_div",
            # )

        except Exception as exception:
            webbrowser.open(path.join(product_pages_folder, product_filename + ".html"))
            sellers_file = path.join(product_pages_folder, product_filename + "-sellers.html")
            if path.isfile(sellers_file):
                webbrowser.open(sellers_file)
            raise exception
            # product_name = get_product_name(product_page)
            # product_data["product_name"] = product_name

            # if has_partial_buyboxes(product_page):
            #     # make all selections
            #     for choice_set_index in range(len(get_choice_sets(product_page))):
            #         get_choice_sets(product_page)[choice_set_index].select(
            #             "ul > li.a-declarative"
            #         )[0].click()

            # amazon_choice_badges = product_page.select(".ac-badge-rectangle")
            # if len(amazon_choice_badges) > 0:
            #     # sanity check
            #     only(amazon_choice_badges)
            #     product_data["amazons_choice"] = True

            # # buyboxes are the thing on the right side with the price etc.
            # # there might be more than one, e.g. one for new and one for used
            # buyboxes = product_page.select("#buyBoxAccordion")
            # if len(buyboxes) > 0:
            #     # sanity check
            #     only(buyboxes)
            #     # use data from the first side box
            #     box_prefix = "#buyBoxAccordion > div:first-child "
            # else:
            #     box_prefix = ""

            # prices = product_page.select(
            #     By.CSS_SELECTOR,
            #     box_prefix
            #     + "#corePrice_feature_div .a-price, "
            #     + box_prefix
            #     + "#booksHeaderSection span#price, "
            #     + box_prefix
            #     + "#usedBuySection div.a-column .offer-price, "
            #     + box_prefix
            #     + "#renewedBuyBoxPrice",
            # )

            # # some of these are not mutually exclusive, so try twice
            # # TODO: figure out what's going on
            # availabilities = product_page.select(
            #     box_prefix + "#availability"
            # )
            # if len(availabilities) == 0:
            #     availabilities = product_page.select(
            #         By.CSS_SELECTOR,
            #         box_prefix
            #         + ".qa-buybox-block .qa-availability-message, "
            #         + box_prefix
            #         + "#exports_desktop_outOfStock_buybox_message_feature_div",
            #     )

            # if len(availabilities) == 0:
            #     # assume it's available unless it says otherwise
            #     available = True
            # else:
            #     availability = only(availabilities).text.strip()
            #     product_data["availability"] = availability
            #     available = not (
            #         availability
            #         == "Currently unavailable.\nWe don't know when or if this item will be back in stock."
            #         or availability
            #         == "Temporarily out of stock.\nWe are working hard to be back in stock as soon as possible."
            #     )



            # if available:
            #     if len(undeliverable_messages) > 0:
            #         product_data["availability"] = only(undeliverable_messages).text.strip()
            #         # sometimes there's still a price even if its undeliverable
            #         # these aren't mutually exclusive so check them seperately
            #         buybox_prices = product_page.select(
            #             box_prefix + "#price_inside_buybox"
            #         )
            #         main_prices = product_page.select(
            #             "#corePrice_desktop span.a-price"
            #         )
            #         if len(buybox_prices) > 0:
            #             product_data["current_price"] = get_price(only(buybox_prices))
            #         elif len(main_prices) > 0:
            #             product_data["current_price"] = get_price(only(main_prices))
            #     elif len(prices) == 0:
            #         # there's a special format for a kindle discount
            #         kindle_discount_prices = product_page.select(
            #             box_prefix + "#kindle-price"
            #         )
            #         if len(kindle_discount_prices) > 0:
            #             product_data["kindle_discount"] = True
            #             # sanity check
            #             only(kindle_discount_prices)
            #             product_data["current_price"] = parse_price(
            #                 only(kindle_discount_prices).text.strip()
            #             )
            #         else:
            #             # and another special format if its only available on kindle
            #             only_kindle_messages = product_page.select(
            #                 box_prefix + "span.no-kindle-offer-message"
            #             )
            #             if len(only_kindle_messages) > 0:
            #                 only(only_kindle_messages)
            #                 product_data["current_price"] = only(
            #                     product_page.select(
            #                         By.CSS_SELECTOR,
            #                         box_prefix + "span.a-button-selected span.a-color-price",
            #                     )
            #                 ).text.strip()
            #             else:
            #                 # for books etc. with many sellers, a single price won't show
            #                 # click to look at the sellers
            #                 only(
            #                     product_page.select(
            #                         By.CSS_SELECTOR,
            #                         box_prefix + "a[title='See All Buying Options']",
            #                     )
            #                 ).click()

            #                 seller_prices = product_page.select(
            #                     By.CSS_SELECTOR,
            #                     "div#aod-offer-list > div:first-of-type span.a-price",
            #                 )
            #                 if len(seller_prices) > 0:
            #                     product_data["current price"] = get_price(only(seller_prices))

            #                 delivery_widgets = product_page.select(
            #                     By.CSS_SELECTOR,
            #                     "#aod-offer-list > div:first-of-type #mir-layout-DELIVERY_BLOCK-slot-PRIMARY_DELIVERY_MESSAGE_LARGE span[data-csa-c-type='element']",
            #                 )

            #                 if len(delivery_widgets) > 0:
            #                     delivery_widget = only(delivery_widgets)
            #                     product_data[
            #                         "shipping_cost_message"
            #                     ] = delivery_widget.get_attribute("data-csa-c-delivery-price")
            #                     product_data["delivery_range"] = delivery_widget.get_attribute(
            #                         "data-csa-c-delivery-time"
            #                     )

            #                 # close the sellers list
            #                 only(
            #                     product_page.select(".aod-close-button")
            #                 ).click()
            #                 # TODO: get more information here
            #     else:
            #         # if there's two prices, the second price is the unit price
            #         if len(prices) == 2:
            #             product_data["current_price"] = get_price(prices[0])
            #             product_data["unit_price"] = get_price(prices[1])
            #             # not a separate element so have to extract from the text

            #             product_data["unit"] = select(
            #                 r"^\(\n.* \/ ?(.*)\)$",
            #                 only(
            #                     product_page.select(
            #                         By.CSS_SELECTOR,
            #                         box_prefix
            #                         + "#corePrice_feature_div :not(#taxInclusiveMessage).a-size-small, #corePrice_feature_div :not(#taxInclusiveMessage).a-size-mini, #corePrice_feature_div span[data-a-size='small']:not(#taxInclusiveMessage)",
            #                     )
            #                 ).text.strip(),
            #             ).group(1)
            #         else:
            #             # sanity check: make sure there's only one price
            #             product_data["current_price"] = get_price(only(prices))

            #         shipped_bys = product_page.select(
            #             By.CSS_SELECTOR,
            #             box_prefix
            #             + "div[tabular-attribute-name='Ships from'] .tabular-buybox-text-message",
            #         )
            #         if len(shipped_bys) > 0:
            #             product_data["shipped_by"] = only(shipped_bys).text.strip()

            #         shipping_cost_messages = product_page.select(
            #             By.CSS_SELECTOR,
            #             box_prefix
            #             + "#price-shipping-message, "
            #             + box_prefix
            #             + "#desktop_qualifiedBuyBox #amazonGlobal_feature_div > .a-color-secondary",
            #         )

            #         # TODO: parse the shipping cost message to get a number
            #         if len(shipping_cost_messages) > 0:
            #             product_data["shipping_cost_message"] = only(
            #                 shipping_cost_messages
            #             ).text.strip()

            #         standard_delivery_dates = product_page.select(
            #             By.CSS_SELECTOR,
            #             box_prefix
            #             + "#mir-layout-DELIVERY_BLOCK-slot-PRIMARY_DELIVERY_MESSAGE_LARGE .a-text-bold",
            #         )

            #         if len(standard_delivery_dates) > 0:
            #             product_data["standard_delivery_date"] = only(
            #                 standard_delivery_dates
            #             ).text.strip()

            #         fastest_delivery_dates = product_page.select(
            #             By.CSS_SELECTOR,
            #             box_prefix
            #             + "#mir-layout-DELIVERY_BLOCK-slot-SECONDARY_DELIVERY_MESSAGE_LARGE .a-text-bold",
            #         )
            #         if len(fastest_delivery_dates) > 0:
            #             product_data["fastest_delivery_date"] = only(
            #                 fastest_delivery_dates
            #             ).text.strip()

            #         list_prices = product_page.select(
            #             By.CSS_SELECTOR,
            #             box_prefix
            #             + "#corePriceDisplay_desktop_feature_div span[data-a-strike='true'], "
            #             + box_prefix
            #             + "#print-list-price "
            #             + box_prefix
            #             + "span#listPrice",
            #         )
            #         if len(list_prices) > 0:
            #             product_data["list_price"] = get_price(only(list_prices))

            #         prime_prices = product_page.select(
            #             box_prefix + "#pep-signup-link .a-size-base"
            #         )
            #         if len(prime_prices) > 0:
            #             product_data["prime_price"] = get_price(only(prime_prices))

            #         #this checks for subscription availability on subcription only products
            #         subscription_legal_text = product_page.select(
            #             "#sndbox-legalText"
            #         )
            #         if len(subscription_legal_text) > 0 and "Automatically renews" in only(subscription_legal_text).text.strip():
            #             product_data["subscription"] = True

            #         #this checks for subscription availability on subcription as an option products
            #         subscription_price = product_page.select(
            #             "span[id='subscriptionPrice']"
            #         )
            #         if len(subscription_price) > 0 and "$" in only(subscription_price).text.strip():
            #             product_data["subscription_price"] = True

            #         return_policy_text = product_page.select(
            #                 "#productSupportAndReturnPolicy-return-policy-anchor-text"
            #         )

            #         if len(return_policy_text) > 0:
            #             product_data["return_policy"] = only(return_policy_text).text.strip()
            #         else:
            #             amazon_renewed_check = product_page.select(
            #                 "#bylineInfo_feature_div .a-link-normal"
            #             )
            #             if len(amazon_renewed_check) > 0 and only(amazon_renewed_check).text.strip() == "Visit the Amazon Renewed Store":
            #                 product_data["return_policy"] = "Amazon Renewed"

            # category_navigation_widget = product_page.select("#wayfinding-breadcrumbs_feature_div")

            # if len(category_navigation_widget) > 0:
            #     category_links = category_navigation_widget[0].select(
            #         "a[class='a-link-normal a-color-tertiary']"
            #     )

            #     for i, link in enumerate(category_links[:5]):
            #         if link and link.text.strip():
            #             product_data[f"sub_category_{i}"] = link.text.strip().replace("\n", "").replace(" ", "")
            #         else:
            #             product_data[f"sub_category_{i}"] = None

    return concat(product_rows, ignore_index=True)
