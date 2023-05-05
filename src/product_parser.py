from pandas import concat, DataFrame
import re
from src.utilities import get_filenames, only, read_html


# e.g. 1,000 -> 1000
def remove_commas(a_string):
    return a_string.replace(",", "")

def get_price(price_widget):
    # some prices have separate dollar and cent parts
    dollar_parts = price_widget.select(".a-price-whole")
    if len(dollar_parts) > 0:
        # dollars
        return (
            int(
                remove_commas(only(price_widget.select(".a-price-whole")).text.strip())
                # cents
            )
            + int(
                remove_commas(
                    only(price_widget.select(".a-price-fraction")).text.strip()
                )
            )
            / 100
        )
    else:
        # others are all together
        return parse_price(price_widget.text.strip())


def parse_price(price_string):
    # ignore the dollar sign in front
    return float(remove_commas(price_string[1:]))


def get_star_percentage(histogram_row):
    return only(histogram_row.select(".a-text-right > .a-size-base")).text.strip()


# sets of choices that one can choose from
def get_choice_sets(page):
    return page.select("#twister-plus-inline-twister > div.inline-twister-row")


# if buy box hasn't fully loaded because its waiting for users to make a choice
def has_partial_buyboxes(page):
    return len(page.select("#partialStateBuybox")) > 0


def get_histogram_rows(page):
    return page.select(
        ", ".join([
            ".cr-widget-TitleRatingsHistogram .a-histogram-row",
            # first span is the number of stars, the div is the bar, and the second span is the percent
            "a[data-automation-id*='histogram-row'] span + div + span"
        ])
    )

class NotFiveHistogramRows(Exception):
    pass

class NotNoReviewsText(Exception):
    pass

class NotUnsupportedText(Exception):
    pass

# product_id = "380"
def parse_product_pages(product_pages_folder, max_products = 10**6):
    product_rows = []
    for (index, product_filename) in enumerate(get_filenames(product_pages_folder)):
        if index > max_products:
            break
        # all digits
        if re.match(r"\-sellers$", product_filename) is None:
            page = read_html(product_pages_folder, product_filename)
        
            try:
                unsupported_browser_widgets = page.select("h2.heading.title")
                if len(unsupported_browser_widgets) > 0:
                    if only(unsupported_browser_widgets).text.strip() != "Your browser is not supported":
                        raise NotUnsupportedText()
                    continue

                video_widgets = page.select("div.av-page-desktop")
                if len(video_widgets) > 0:
                    # sanity check
                    only(video_widgets)
                    continue
                
                music_widgets = page.select("music-app")
                if len(music_widgets) > 0:
                    # sanity check
                    only(music_widgets)
                    continue

                medication_widgets = page.select("a#nav-link-pharmacy-home-desktop")
                if len(medication_widgets) > 0:
                    only(medication_widgets)
                    continue
                
                no_reviews_widgets = page.select(
                    ", ".join([
                        "span[data-hook='top-customer-reviews-title']",
                        "#cm_cr_dp_d_rating_histogram span.a-text-bold"
                    ])
                )
                if len(no_reviews_widgets) > 0:
                    no_reviews_text = only(no_reviews_widgets).text.strip()
                    if not (no_reviews_text == "No customer reviews" or no_reviews_text == "There are no customer ratings or reviews for this product."):
                        raise NotNoReviewsText()
                    has_reviews = False
                
                    ratings_but_no_reviews_widgets = page.select(
                        "div.review div.a-box-inner"
                    )
                    if len(ratings_but_no_reviews_widgets) > 0:
                        # sanity check
                        only(ratings_but_no_reviews_widgets)                       
                        has_ratings = True
                    else:
                        has_ratings = False
                else:
                    has_reviews = True
                    has_ratings = True

                # ratings arent displayed for videos
                if has_ratings:
                    average_rating = float(
                        re.search(
                            r"^(.*) out of 5$", only(page.select(
                                "span.cr-widget-TitleRatingsHistogram span[data-hook='rating-out-of-text']"
                            )).text.strip()
                        ).group(1)
                    )
                    number_of_ratings = int(
                        remove_commas(
                            re.search(
                                r"^(.*) global ratings?$",
                                only(
                                    page.select(
                                        "span.cr-widget-TitleRatingsHistogram [data-hook='total-review-count']", 
                                    )
                                ).text.strip(),
                            ).group(1)
                        )
                    )
                    histogram_rows = page.select(
                        ".cr-widget-TitleRatingsHistogram .a-histogram-row"
                    )
                    if len(histogram_rows) != 5:
                        raise NotFiveHistogramRows()

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

                product_rows.append(DataFrame({
                    "product_filename": product_filename,
                    "average_rating": average_rating,
                    "has_reviews": has_reviews,
                    "number_of_ratings": number_of_ratings,
                    "one_star_percentage": one_star_percentage,
                    "two_star_percentage": two_star_percentage,
                    "three_star_percentage": three_star_percentage,
                    "four_star_percentage": four_star_percentage,
                    "five_star_percentage": five_star_percentage
                }, index = [0]))

                # undeliverable_messages = page.select(
                #     By.CSS_SELECTOR,
                #     box_prefix
                #     + "#exports_desktop_undeliverable_buybox_priceInsideBuybox_feature_div",
                # )

            except Exception as exception:
                print(product_filename)
                raise exception
            # product_name = get_product_name(page)
            # product_data["product_name"] = product_name

            # if has_partial_buyboxes(page):
            #     # make all selections
            #     for choice_set_index in range(len(get_choice_sets(page))):
            #         get_choice_sets(page)[choice_set_index].select(
            #             "ul > li.a-declarative"
            #         )[0].click()

            # amazon_choice_badges = page.select(".ac-badge-rectangle")
            # if len(amazon_choice_badges) > 0:
            #     # sanity check
            #     only(amazon_choice_badges)
            #     product_data["amazons_choice"] = True

            # # buyboxes are the thing on the right side with the price etc.
            # # there might be more than one, e.g. one for new and one for used
            # buyboxes = page.select("#buyBoxAccordion")
            # if len(buyboxes) > 0:
            #     # sanity check
            #     only(buyboxes)
            #     # use data from the first side box
            #     box_prefix = "#buyBoxAccordion > div:first-child "
            # else:
            #     box_prefix = ""

            # prices = page.select(
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
            # availabilities = page.select(
            #     box_prefix + "#availability"
            # )
            # if len(availabilities) == 0:
            #     availabilities = page.select(
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
            #         buybox_prices = page.select(
            #             box_prefix + "#price_inside_buybox"
            #         )
            #         main_prices = page.select(
            #             "#corePrice_desktop span.a-price"
            #         )
            #         if len(buybox_prices) > 0:
            #             product_data["current_price"] = get_price(only(buybox_prices))
            #         elif len(main_prices) > 0:
            #             product_data["current_price"] = get_price(only(main_prices))
            #     elif len(prices) == 0:
            #         # there's a special format for a kindle discount
            #         kindle_discount_prices = page.select(
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
            #             only_kindle_messages = page.select(
            #                 box_prefix + "span.no-kindle-offer-message"
            #             )
            #             if len(only_kindle_messages) > 0:
            #                 only(only_kindle_messages)
            #                 product_data["current_price"] = only(
            #                     page.select(
            #                         By.CSS_SELECTOR,
            #                         box_prefix + "span.a-button-selected span.a-color-price",
            #                     )
            #                 ).text.strip()
            #             else:
            #                 # for books etc. with many sellers, a single price won't show
            #                 # click to look at the sellers
            #                 only(
            #                     page.select(
            #                         By.CSS_SELECTOR,
            #                         box_prefix + "a[title='See All Buying Options']",
            #                     )
            #                 ).click()

            #                 seller_prices = page.select(
            #                     By.CSS_SELECTOR,
            #                     "#aod-offer-list > div:first-of-type .a-price",
            #                 )
            #                 if len(seller_prices) > 0:
            #                     product_data["current price"] = get_price(only(seller_prices))

            #                 delivery_widgets = page.select(
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
            #                     page.select(".aod-close-button")
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
            #                     page.select(
            #                         By.CSS_SELECTOR,
            #                         box_prefix
            #                         + "#corePrice_feature_div :not(#taxInclusiveMessage).a-size-small, #corePrice_feature_div :not(#taxInclusiveMessage).a-size-mini, #corePrice_feature_div span[data-a-size='small']:not(#taxInclusiveMessage)",
            #                     )
            #                 ).text.strip(),
            #             ).group(1)
            #         else:
            #             # sanity check: make sure there's only one price
            #             product_data["current_price"] = get_price(only(prices))

            #         shipped_bys = page.select(
            #             By.CSS_SELECTOR,
            #             box_prefix
            #             + "div[tabular-attribute-name='Ships from'] .tabular-buybox-text-message",
            #         )
            #         if len(shipped_bys) > 0:
            #             product_data["shipped_by"] = only(shipped_bys).text.strip()

            #         shipping_cost_messages = page.select(
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

            #         standard_delivery_dates = page.select(
            #             By.CSS_SELECTOR,
            #             box_prefix
            #             + "#mir-layout-DELIVERY_BLOCK-slot-PRIMARY_DELIVERY_MESSAGE_LARGE .a-text-bold",
            #         )

            #         if len(standard_delivery_dates) > 0:
            #             product_data["standard_delivery_date"] = only(
            #                 standard_delivery_dates
            #             ).text.strip()

            #         fastest_delivery_dates = page.select(
            #             By.CSS_SELECTOR,
            #             box_prefix
            #             + "#mir-layout-DELIVERY_BLOCK-slot-SECONDARY_DELIVERY_MESSAGE_LARGE .a-text-bold",
            #         )
            #         if len(fastest_delivery_dates) > 0:
            #             product_data["fastest_delivery_date"] = only(
            #                 fastest_delivery_dates
            #             ).text.strip()

            #         list_prices = page.select(
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

            #         prime_prices = page.select(
            #             box_prefix + "#pep-signup-link .a-size-base"
            #         )
            #         if len(prime_prices) > 0:
            #             product_data["prime_price"] = get_price(only(prime_prices))

            #         #this checks for subscription availability on subcription only products
            #         subscription_legal_text = page.select(
            #             "#sndbox-legalText"
            #         )
            #         if len(subscription_legal_text) > 0 and "Automatically renews" in only(subscription_legal_text).text.strip():
            #             product_data["subscription"] = True

            #         #this checks for subscription availability on subcription as an option products
            #         subscription_price = page.select(
            #             "span[id='subscriptionPrice']"
            #         )
            #         if len(subscription_price) > 0 and "$" in only(subscription_price).text.strip():
            #             product_data["subscription_price"] = True

            #         return_policy_text = page.select(
            #                 "#productSupportAndReturnPolicy-return-policy-anchor-text"
            #         )

            #         if len(return_policy_text) > 0:
            #             product_data["return_policy"] = only(return_policy_text).text.strip()
            #         else:
            #             amazon_renewed_check = page.select(
            #                 "#bylineInfo_feature_div .a-link-normal"
            #             )
            #             if len(amazon_renewed_check) > 0 and only(amazon_renewed_check).text.strip() == "Visit the Amazon Renewed Store":
            #                 product_data["return_policy"] = "Amazon Renewed"

            # category_navigation_widget = page.select("#wayfinding-breadcrumbs_feature_div")

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
