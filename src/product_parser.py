from bs4 import Tag
from os import path
from pandas import concat, DataFrame
import re
from src.utilities import get_filenames, only, read_html
import webbrowser

def find_product(product_pages_folder, selector):
    for product_filename in get_filenames(product_pages_folder):
        product_page = read_html(product_pages_folder, product_filename)
        if len(product_page.select(selector)) > 0:
            webbrowser.open(path.join(product_pages_folder, product_filename + ".html"))
            break

def is_complicated(product_page):
    unsupported_browser_widgets = product_page.select("h2.heading.title")
    if len(unsupported_browser_widgets) > 0:
        if only(unsupported_browser_widgets).text.strip() != "Your browser is not supported":
            raise NotUnsupported()
        return True
    
    book_widgets = product_page.select("div.book")
    if len(book_widgets) > 0:
        only(book_widgets)
        return True
    
    ebook_widgets = product_page.select("div#dp.ebooks")
    if len(ebook_widgets) > 0:
        only(ebook_widgets)
        return True
    
    e_magazine_widgets = product_page.select("div.digitaltextfeeds")
    if len(e_magazine_widgets) > 0:
        only(e_magazine_widgets)
        return True
    
    digital_music_widgets = product_page.select("music-app")
    if len(digital_music_widgets) > 0:
        # sanity check
        only(digital_music_widgets)
        return True

    digital_video_widgets = product_page.select(",".join([
        "div.av-product_page-desktop", 
        "div.av-page-desktop"
    ]))
    if len(digital_video_widgets) > 0:
        # sanity check
        only(digital_video_widgets)
        return True
    
    digital_software_widgets = product_page.select("div.digital_software")
    if len(digital_software_widgets) > 0:
        only(digital_software_widgets)
        return True
    
    mobile_widgets = product_page.select("div.device-type-desktop")
    if len(mobile_widgets):
        only(mobile_widgets)
        return True
    
    app_widgets = product_page.select("div.masrw-box")
    if len(app_widgets) > 0:
        only(app_widgets)
        return True
    
    alexa_skill_widgets = product_page.select("img[data-cy='alexa-free-skill-logo']")
    if len(alexa_skill_widgets):
        only(alexa_skill_widgets)
        return True
    
    medication_widgets = product_page.select("a#nav-link-pharmacy-home-desktop")
    if len(medication_widgets) > 0:
        only(medication_widgets)
        return True
    
    gift_card_widgets = product_page.select("div#gc-detail-page")
    if len(gift_card_widgets) > 0:
        only(gift_card_widgets)
        return True
    
    subscription_widgets = product_page.select("div#sndboxBuyBox_feature_div")
    if len(subscription_widgets) > 0:
        only(subscription_widgets)
        return True
    
    audible_widgets = product_page.select("div.audible")
    if len(audible_widgets) > 0:
        only(audible_widgets)
        return True
    
    choose_seller_widgets = product_page.select("a[title='See All Buying Options']")
    if len(choose_seller_widgets) > 0:
        only(choose_seller_widgets)
        return True
    
    return False

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

# product_id = "380"
def parse_product_pages(product_pages_folder):
    product_rows = []
    for product_filename in get_filenames(product_pages_folder):
        # all digits
        if re.match(r"\-sellers$", product_filename) is None:
            product_page = read_html(product_pages_folder, product_filename)
        
            try:
                if is_complicated(product_page):
                    continue

                no_ratings_or_reviews_widgets = product_page.select(
                    "#cm_cr_dp_d_rating_histogram span.a-text-bold"
                )
                no_reviews_widgets = product_page.select(
                    "span[data-hook='top-customer-reviews-title']"
                )
                
                if len(no_ratings_or_reviews_widgets) > 0:
                    if only(no_ratings_or_reviews_widgets).text.strip() != "There are no customer ratings or reviews for this product.":
                        raise NotNoReviews()
                    has_ratings = False
                    has_reviews = False
                elif len(no_reviews_widgets) > 0:
                    if only(no_reviews_widgets).text.strip() != "No customer reviews":
                        raise NotNoReviews()
                    has_reviews = False

                    ratings_summary_widgets = product_page.select(
                        "div.review"
                    )
                    if len(ratings_summary_widgets) > 0:
                        if re.search(
                            r"^There are 0 customer reviews and (.*) customer ratings?\.$",
                            only(ratings_summary_widgets).text.strip(),
                        ) is None:
                            raise NotReviewSummary()
                        has_ratings = True
                    else:
                        has_ratings = False
                else:
                    has_ratings = True
                    has_reviews = True

                if has_ratings:
                    ratings_widget = only(product_page.select(
                        "span.cr-widget-TitleRatingsHistogram"
                    ))
                    average_rating = float(
                        re.search(
                            r"^(.*) out of 5$", only(ratings_widget.select(
                                "span[data-hook='rating-out-of-text']"
                            )).text.strip()
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
                else:
                    average_rating = None
                    number_of_ratings = None
                    one_star_percentage = None
                    two_star_percentage = None
                    three_star_percentage = None
                    four_star_percentage = None
                    five_star_percentage = None
                
                hidden_price_widgets = product_page.select("a[href='/forum/where%20is%20the%20price']")
                if len(hidden_price_widgets) > 0:
                    hidden_prices = True
                else:
                    hidden_prices = False

                if hidden_prices:
                    price = None
                    unit_price = None
                else:
                    accordion_rows = product_page.select("#buyBoxAccordion div[id*='AccordionRow']")
                    if len(accordion_rows) > 0:
                        buybox = accordion_rows[0]
                    else:
                        buybox_group = only(product_page.select("div[data-csa-c-content-id='desktop_buybox_group_1']"))
                        buybox = only(buybox_group.select(", ".join([
                            "div#qualifiedBuybox",
                            "div#qualifiedBuybox_globalMatchbox_3",
                            "div#usedOnlyBuybox",
                            "div#outOfStockBuyBox_feature_div",
                            "div#exportsBuybox",
                        ])))
                    
                    buybox_id = buybox.get("id")
                    if buybox_id == "usedOnlyBuybox":
                        price = get_price(only(buybox.select("div.a-grid-center span.offer-price")))
                        unit_price = None
                        undeliverable = False
                        out_of_stock = False
                    elif buybox_id == "renewedTier2AccordionRow":
                        price = get_price(only(buybox.select("span#renewedBuyBoxPrice")))
                        unit_price = None
                        undeliverable = False
                        out_of_stock = False
                    elif buybox_id == "newAccordionRow_0":
                        undeliverable = False
                        out_of_stock_widgets = buybox.select("div#outOfStock")
                        if len(out_of_stock_widgets) > 0:
                            only(out_of_stock_widgets)
                            out_of_stock = True
                            price = None
                            unit_price = None
                        else:
                            out_of_stock = False
                            price_widgets = buybox.select("div#corePrice_feature_div span.a-offscreen")
                            if len(price_widgets) == 1:
                                price = get_price(price_widgets[0])
                                unit_price = None
                            elif len(price_widgets) == 2:
                                price = get_price(price_widgets[0])
                                unit_price = get_price(price_widgets[0])
                            else:
                                raise NotOneOrTwoPrices()
                    elif buybox_id == "qualifiedBuybox":
                        undeliverable = False
                        out_of_stock_widgets = buybox.select("div#outOfStock")
                        if len(out_of_stock_widgets) > 0:
                            only(out_of_stock_widgets)
                            out_of_stock = True
                            price = None
                            unit_price = None
                        else:
                            out_of_stock = False
                            price_widgets = buybox.select("div#corePrice_feature_div span.a-offscreen")
                            if len(price_widgets) == 1:
                                price = get_price(price_widgets[0])
                                unit_price = None
                            elif len(price_widgets) == 2:
                                price = get_price(price_widgets[0])
                                unit_price = get_price(price_widgets[0])
                            else:
                                raise NotOneOrTwoPrices()
                    elif buybox_id == "qualifiedBuybox_globalMatchbox_3":
                        undeliverable = False
                        out_of_stock_widgets = buybox.select("div#outOfStock")
                        if len(out_of_stock_widgets) > 0:
                            only(out_of_stock_widgets)
                            out_of_stock = True
                            price = None
                            unit_price = None
                        else:
                            out_of_stock = False
                            price_widgets = buybox.select("div#corePrice_feature_div span.a-offscreen")
                            if len(price_widgets) == 1:
                                price = get_price(price_widgets[0])
                                unit_price = None
                            elif len(price_widgets) == 2:
                                price = get_price(price_widgets[0])
                                unit_price = get_price(price_widgets[0])
                            else:
                                raise NotOneOrTwoPrices()
                    elif buybox_id == "newAccordionRow":
                        undeliverable = False
                        out_of_stock_widgets = buybox.select("div#outOfStock")
                        if len(out_of_stock_widgets) > 0:
                            only(out_of_stock_widgets)
                            out_of_stock = True
                            price = None
                            unit_price = None
                        else:
                            out_of_stock = False
                            price_widgets = buybox.select("div#corePrice_feature_div span.a-offscreen")
                            if len(price_widgets) == 1:
                                price = get_price(price_widgets[0])
                                unit_price = None
                            elif len(price_widgets) == 2:
                                price = get_price(price_widgets[0])
                                unit_price = get_price(price_widgets[0])
                            else:
                                raise NotOneOrTwoPrices()
                    elif buybox_id == "exportsBuybox":
                        undeliverable_widgets = buybox.select("div#exports_desktop_undeliverable_buybox")
                        out_of_stock_widgets = buybox.select("div#outOfStock")
                        if len(out_of_stock_widgets) > 0:
                            only(out_of_stock_widgets)
                            out_of_stock = True
                            undeliverable = False
                            price = None
                            unit_price = None
                        elif len(undeliverable_widgets) > 0:
                            only(undeliverable_widgets)
                            out_of_stock = False
                            undeliverable = True
                            price = None
                            unit_price = None
                        else:
                            undeliverable = False
                            out_of_stock = False
                            price_widgets = buybox.select("div#corePrice_feature_div span.a-offscreen")
                            if len(price_widgets) == 1:
                                price = get_price(price_widgets[0])
                                unit_price = None
                            elif len(price_widgets) == 2:
                                price = get_price(price_widgets[0])
                                unit_price = get_price(price_widgets[0])
                            else:
                                raise NotOneOrTwoPrices()
                    elif buybox_id == "outOfStockBuyBox_feature_div":
                        price = None
                        unit_price = None
                        out_of_stock = True
                        undeliverable = False
                    elif buybox_id == "dealsAccordionRow":
                        price_widgets = buybox.select("div#corePrice_feature_div span.a-offscreen")
                        if len(price_widgets) == 1:
                            price = get_price(price_widgets[0])
                            unit_price = None
                        elif len(price_widgets) == 2:
                            price = get_price(price_widgets[0])
                            unit_price = get_price(price_widgets[0])
                        else:
                            raise NotOneOrTwoPrices()

                    else:
                        raise UnrecognizedBuybox(buybox_id)
                    
                print(product_filename)

                product_rows.append(DataFrame({
                    "product_filename": product_filename,
                    "average_rating": average_rating,
                    "has_reviews": has_reviews,
                    "number_of_ratings": number_of_ratings,
                    "one_star_percentage": one_star_percentage,
                    "two_star_percentage": two_star_percentage,
                    "three_star_percentage": three_star_percentage,
                    "four_star_percentage": four_star_percentage,
                    "five_star_percentage": five_star_percentage,
                    "price": price,
                    "unit_price": unit_price,
                    "out_of_stock": out_of_stock,
                    "undeliverable": undeliverable,
                    "hidden_prices": hidden_prices
                }, index = [0]))

                # undeliverable_messages = product_page.select(
                #     By.CSS_SELECTOR,
                #     box_prefix
                #     + "#exports_desktop_undeliverable_buybox_priceInsideBuybox_feature_div",
                # )

            except Exception as exception:
                webbrowser.open(path.join(product_pages_folder, product_filename + ".html"))
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
            #                     "#aod-offer-list > div:first-of-type .a-price",
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
