from bs4 import BeautifulSoup
from os import chdir, path
import re

FOLDER = "/home/brandon/amazon_scraper"
chdir(FOLDER)
from utilities import dicts_to_dataframe, get_filenames, only


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
    return page.select(".cr-widget-TitleRatingsHistogram .a-histogram-row")


def get_product_name(page):
    title_elements = page.select(
        "span#productTitle, span.qa-title-text, h1[data-automation-id='title']"
    )
    if len(title_elements) > 0:
        return only(title_elements).text.strip()

    return only(page.select("h1[data-testid='title-art'] img"))["alt"]


# filename = "380"
def parse_product_pages(product_pages_folder):
    product_rows = []
    for filename in get_filenames(product_pages_folder):
        # all digits
        if not (re.match(r"^\d+$", filename) is None):
            product_data = {}
            file = open(path.join(product_pages_folder, filename + ".html"), "r")
            page = BeautifulSoup(file, "lxml")
            try:
                product_data["product_name"] = get_product_name(page)
                average_ratings = page.select(
                    ".cr-widget-TitleRatingsHistogram span[data-hook='rating-out-of-text']",
                )
                if len(average_ratings) > 0:
                    # TODO: sanity check verify no ratings
                    product_data["average_rating"] = float(
                        re.search(
                            r"^(.*) out of 5$", only(average_ratings).text.strip()
                        ).group(1)
                    )
                    product_data["number_of_ratings"] = int(
                        remove_commas(
                            re.search(
                                r"^(.*) global ratings?$",
                                only(
                                    page.select(
                                        '.cr-widget-TitleRatingsHistogram div[data-hook="total-review-count"], .cr-widget-TitleRatingsHistogram span[data-hook="total-review-count"]'
                                    )
                                ).text.strip(),
                            ).group(1)
                        )
                    )
                    histogram_rows = page.select(
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
                        histogram_rows[3]
                    )
                    product_data["one_star_percentage"] = get_star_percentage(
                        histogram_rows[4]
                    )
            except Exception as exception:
                print(filename)
                file.close()
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

            # undeliverable_messages = page.select(
            #     By.CSS_SELECTOR,
            #     box_prefix
            #     + "#exports_desktop_undeliverable_buybox_priceInsideBuybox_feature_div",
            # )

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

            file.close()
            product_rows.append(product_data)

    return dicts_to_dataframe(product_rows)
