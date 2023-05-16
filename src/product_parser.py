from os import listdir, path
from pandas import concat, DataFrame
import re
from src.utilities import combine_folder_csvs, get_filenames, only, read_html
import webbrowser
from datetime import date

# convert fakespot grades to a numerical rank
# this is still ordinal, not cardinal
FAKESPOT_RANKINGS = {"A": 1, "B": 2, "C": 3, "D": 4, "F": 5, "?": None}


def get_star_percent(histogram_row):
    return int(
        re.fullmatch(
            r"(\d)+%", only(histogram_row.select("td.a-text-right")).text
        ).group(1)
    )


# debugging function for finding particular product pages
def find_products(product_pages_folder, a_function, number_of_products=5):
    found = 0
    for product_id in listdir(product_pages_folder):
        product_file = path.join(product_pages_folder, product_id)
        product_page = read_html(product_file)
        if a_function(product_page):
            webbrowser.open(product_file)
            found = found + 1
            if found == number_of_products:
                break


# error if there aren't rows for each of 1-5 stars
class NotFiveRows(Exception):
    pass


# error if we misidentify an unsupported browser pages
class NotUnsupported(Exception):
    pass


# there should be either just one price, or a price and a unit price
class NotOneOrTwoPrices(Exception):
    pass


def parse_bestseller_rank(product_id, best_seller_widget, index):
    return DataFrame(
        {
            "order": index + 1,
            "product_id": product_id,
            "best_seller_text": best_seller_widget.text,
        },
        index=[0],
    ).set_index("product_id")


def remove_commas(a_string):
    return a_string.replace(",", "")


def parse_price(price_text):
    # dollar sign, then digits and decimal
    return float(re.fullmatch(r"\$([\d\.]+)", remove_commas(price_text)).group(1))


# convert month names to numbers
MONTH_NUMBERS = {
    "January": 1,
    "February": 2,
    "March": 3,
    "April": 4,
    "May": 5,
    "June": 6,
    "July": 7,
    "August": 8,
    "September": 9,
    "October": 10,
    "November": 11,
    "December": 12,
}


def parse_dates(date_text, current_year):
    # TODO: dates in the next year?

    # date range with different months
    # e.g. January 1 - February 10
    multi_month_match = re.search(r"(\w+) (\d+) \- (\w+) (\d+)", date_text)
    if not multi_month_match is None:
        return date(
            current_year,
            MONTH_NUMBERS[multi_month_match.group(1)],
            int(multi_month_match.group(2)),
        ), date(
            current_year,
            MONTH_NUMBERS[multi_month_match.group(3)],
            int(multi_month_match.group(4)),
        )

    # date range within one month
    # e.g. January 1 - 4
    single_month_match = re.search(r"(\w+) (\d+) \- (\d+)", date_text)
    if not single_month_match is None:
        month_number = MONTH_NUMBERS[single_month_match.group(1)]
        return date(current_year, month_number, int(single_month_match.group(2))), date(
            current_year, month_number, int(single_month_match.group(3))
        )

    # single date
    # e.g. January 1
    single_day_match = re.search(r"(\w+) (\d+)", date_text)
    if not single_day_match is None:
        return (
            date(
                current_year,
                MONTH_NUMBERS[single_day_match.group(1)],
                int(single_day_match.group(2)),
            ),
            None,
        )


def parse_list_price(pricebox):
    list_price_widgets = pricebox.select(
        "span.a-price[data-a-strike='true'] span.a-offscreen"
    )
    if list_price_widgets:
        return parse_price(only(list_price_widgets).text)

    return None


def parse_coupon(promo_widget):
    coupon_amount = None
    coupon_percent = None
    subscribe_coupon = False

    coupon_widgets = promo_widget.select("label[id*='couponText']")
    if coupon_widgets:
        coupon_text = only(coupon_widgets).contents[0].text
        coupon_amount_match = re.fullmatch(r"Apply \$([\d+\.]) coupon", coupon_text)
        coupon_percent_match = re.fullmatch(r"Apply ([\d+\.,])% coupon", coupon_text)
        if not coupon_amount_match is None:
            coupon_amount = float(remove_commas(coupon_amount_match.group(1)))
        elif not coupon_percent_match is None:
            coupon_percent = float(remove_commas(coupon_percent_match.group(1)))
        else:
            # otherwise, it's most likely just a subscription coupon
            subscribe_coupon = True

    return (coupon_amount, coupon_percent, subscribe_coupon)


def parse_buybox(buybox, current_year):
    # add defaults for all our variables
    free_prime_shipping = False
    free_returns = False
    limited_stock = False
    out_of_stock = False
    price = None
    primary_shipping_conditional = False
    primary_shipping_cost = None
    primary_shipping_date_start = None
    primary_shipping_date_end = None
    return_within_days = 0
    returns_text = ""
    secondary_shipping_date_start = None
    secondary_shipping_date_end = None
    ships_from_amazon = False
    sold_by_amazon = None
    undeliverable = False
    unit = "Purchase"
    unit_price = None

    out_of_stock_widgets = buybox.select("div#outOfStock")
    if out_of_stock_widgets:
        only(out_of_stock_widgets)
        out_of_stock = True

    undeliverable_widgets = buybox.select("div#exports_desktop_undeliverable_buybox")
    if undeliverable_widgets:
        only(undeliverable_widgets)
        undeliverable = True

    # price and unit price
    price_pair_widgets = buybox.select("div#corePrice_feature_div")
    if price_pair_widgets:
        price_pair_widget = only(price_pair_widgets)
        price_widgets = price_pair_widget.select("span.a-offscreen")
        if len(price_widgets) >= 1:
            price = parse_price(price_widgets[0].text)
        if len(price_widgets) >= 2:
            unit_price = parse_price(price_widgets[1].text)
            unit = (
                re.fullmatch(
                    # e.g "/ Fl Oz )"
                    r"\/(.*)\)",
                    only(price_pair_widget.select("span#taxInclusiveMessage + span"))
                    .contents[2]
                    .text,
                )
                .group(1)
                .strip()
            )

        if len(price_widgets) >= 3:
            raise NotOneOrTwoPrices()

    free_prime_shipping_widgets = buybox.select("span#price-shipping-message")
    if free_prime_shipping_widgets:
        free_prime_shipping = True

    availability_widgets = buybox.select("div#availability span")
    if availability_widgets:
        availability_text = only(availability_widgets).text
        if re.fullmatch(
            r"Only ([\d\,]+) left in stock - order soon", availability_text
        ):
            limited_stock = True

    free_returns_widgets = buybox.select("a#creturns-policy-anchor-text")
    if free_returns_widgets:
        free_returns = True

    primary_shipping_widgets = buybox.select(
        "div#mir-layout-DELIVERY_BLOCK-slot-PRIMARY_DELIVERY_MESSAGE_LARGE > span[data-csa-c-content-id*='DEXUnified']"
    )
    if primary_shipping_widgets:
        primary_shipping_widget = only(primary_shipping_widgets)
        (primary_shipping_date_start, primary_shipping_date_end) = parse_dates(
            primary_shipping_widget["data-csa-c-delivery-time"], current_year
        )
        primary_shipping_cost_text = primary_shipping_widget[
            "data-csa-c-delivery-price"
        ]
        if primary_shipping_cost_text == "FREE":
            primary_shipping_cost = 0.0
        elif primary_shipping_cost_text != "":
            primary_shipping_cost = parse_price(primary_shipping_cost_text)
        if primary_shipping_widget["data-csa-c-delivery-condition"] != "":
            primary_shipping_conditional = True

    secondary_shipping_widgets = buybox.select(
        "div#mir-layout-DELIVERY_BLOCK-slot-SECONDARY_DELIVERY_MESSAGE_LARGE > span[data-csa-c-content-id*='DEXUnified']"
    )
    if secondary_shipping_widgets:
        (secondary_shipping_date_start, secondary_shipping_date_end) = parse_dates(
            only(secondary_shipping_widgets)["data-csa-c-delivery-time"], current_year
        )

    ships_from_widgets = buybox.select(
        "div.tabular-buybox-text[tabular-attribute-name='Ships from']"
    )
    if ships_from_widgets:
        ships_from_amazon = "Amazon" in only(ships_from_widgets).text

    sold_by_widgets = buybox.select(
        "div.tabular-buybox-text[tabular-attribute-name='Sold by']"
    )
    if sold_by_widgets:
        sold_by_amazon = "Amazon" in only(sold_by_widgets).text

    returns_text_widgets = buybox.select(
        "div.tabular-buybox-text[tabular-attribute-name='Returns'] span.tabular-buybox-text-message"
    )
    if returns_text_widgets:
        returns_text = only(returns_text_widgets).text
        if returns_text != "Eligible for Refund or Replacement":
            return_within_days = int(
                re.fullmatch(
                    r"Eligible for Return, Refund or Replacement within ([\d]+) days of receipt",
                    returns_text,
                ).group(1)
            )

    return (
        free_prime_shipping,
        free_returns,
        limited_stock,
        out_of_stock,
        price,
        primary_shipping_conditional,
        primary_shipping_cost,
        primary_shipping_date_start,
        primary_shipping_date_end,
        return_within_days,
        secondary_shipping_date_start,
        secondary_shipping_date_end,
        ships_from_amazon,
        sold_by_amazon,
        undeliverable,
        unit_price,
        unit,
    )


def parse_product_page(
    product_rows,
    category_rows,
    best_seller_rows,
    product_pages_folder,
    product_id,
    current_year,
):
    # add defaults for all our variables
    answered_questions = 0
    amazons_choice = False
    average_rating = None
    climate_friendly = False
    coupon_amount = 0.0
    coupon_percent = None
    fakespot_ranking = None
    free_prime_shipping = False
    free_returns = False
    hidden_prices = False
    limited_stock = False
    list_price = None
    new_seller = False
    non_returnable_text = ""
    number_of_ratings = None
    out_of_stock = False
    price = None
    primary_shipping_conditional = False
    primary_shipping_cost = None
    primary_shipping_date_start = None
    primary_shipping_date_end = None
    refurbished = False
    return_within_days = 0
    secondary_shipping_date_start = None
    secondary_shipping_date_end = None
    ships_from_amazon = False
    small_business = False
    sold_by_amazon = None
    subscription_available = False
    subscribe_coupon = False
    undeliverable = False
    unit = "Purchase"
    unit_price = None
    used_only = False

    one_star_percent = None
    two_star_percent = None
    three_star_percent = None
    four_star_percent = None
    five_star_text = None

    product_page = read_html(path.join(product_pages_folder, product_id + ".html"))

    # return without doing anything for a variety of non-standard product pages
    unsupported_browser_widgets = product_page.select("h2.heading.title")
    if unsupported_browser_widgets:
        # this is a non-specific CSS selector, so check the text too
        if (
            not "Your browser is not supported"
            in only(unsupported_browser_widgets).text
        ):
            raise NotUnsupported()
        return

    # can't find the product, so consider alternatives
    consider_alternative_widgets = product_page.select("div#percolate-ui-lpo_div")
    if consider_alternative_widgets:
        only(consider_alternative_widgets)
        return

    # this is heading that contains the product department
    # if the heading is missing, it's not really a product
    # like a link to the Amazon music player, etc.
    product_type_widgets = product_page.select("div#dp")
    if not product_type_widgets:
        return

    product_department = only(product_type_widgets)["class"][0]

    used_only_widgets = product_page.select("div#usedOnlyBuybox")
    if used_only_widgets:
        only(used_only_widgets)
        used_only = True

    refurbished_options = product_page.select(
        "div#buyBoxAccordion > div[id*='renewed']"
    )
    if refurbished_options:
        refurbished = True

    for index, category_widget in enumerate(
        product_page.select("div#wayfinding-breadcrumbs_feature_div a")
    ):
        category_rows.append(
            DataFrame(
                {
                    # +1 for 1 based indexing
                    "order": index + 1,
                    "category": category_widget.text,
                    "product_id": product_id,
                },
                index=[0],
            ).set_index("product_id")
        )

    answered_questions_widgets = product_page.select("a#askATFLink span.a-size-base")
    if answered_questions_widgets:
        answered_questions_text = remove_commas(only(answered_questions_widgets).text)
        # won't show more than 1000
        if answered_questions_text == "1000+ answered questions":
            answered_questions = 1000
        else:
            answered_questions = int(
                re.fullmatch(
                    r"([\d]+) answered questions",
                    remove_commas(only(answered_questions_widgets).text),
                ).group(1)
            )

    amazons_choice_widgets = product_page.select("div#acBadge_feature_div")
    if amazons_choice_widgets:
        only(amazons_choice_widgets)
        amazons_choice = True

    climate_friendly_widgets = product_page.select("div#climatePledgeFriendly")
    if climate_friendly_widgets:
        only(climate_friendly_widgets)
        climate_friendly = True

    small_business_widgets = product_page.select(
        "div.provenance-certifications-row img[src='https://m.media-amazon.com/images/I/111mHoVK0kL._AC_UL34_SS42_.png']"
    )
    if small_business_widgets:
        only(small_business_widgets)
        small_business = True

    center_priceboxes = product_page.select("div#apex_desktop")
    if center_priceboxes:
        center_pricebox = only(center_priceboxes)
        center_pricebox_sets = center_pricebox.select("div.offersConsistencyEnabled")
        if center_pricebox_sets:
            # the invisible ones will have style='hidden'
            visible_priceboxes = only(center_pricebox_sets).select("div[style='']")
            if visible_priceboxes:
                list_price = parse_list_price(only(visible_priceboxes))
            else:
                list_price = parse_list_price(center_pricebox)

    promo_widgets = product_page.select("div#promoPriceBlockMessage_feature_div")
    if promo_widgets:
        promo_widget = only(promo_widgets)
        promo_widget_sets = promo_widget.select("div.offersConsistencyEnabled")
        if promo_widget_sets:
            # the invisible ones will have style='hidden'
            visible_promo_widgets = only(promo_widget_sets).select("div[style='']")
            if visible_promo_widgets:
                (coupon_amount, coupon_percent, subscribe_coupon) = parse_coupon(
                    only(visible_promo_widgets)
                )
        else:
            (coupon_amount, coupon_percent, subscribe_coupon) = parse_coupon(
                promo_widget
            )

    hidden_price_widgets = product_page.select(
        "a[href='/forum/where%20is%20the%20price']"
    )
    if hidden_price_widgets:
        only(hidden_price_widgets)
        hidden_prices = True

    # best seller ranks are in the details
    # details are either formatted as bullets or a table

    # table details
    # best seller links are easy to find
    for index, best_seller_link in enumerate(
        product_page.select("div#prodDetails a[href*='/gp/bestsellers']")
    ):
        # the parent of the best seller link is the best seller row
        best_seller_rows.append(
            parse_bestseller_rank(product_id, best_seller_link.parent, index)
        )

    # bullet details
    # if there are more than one, the first best seller bullet one will contain the rest
    # again, best seller links are easy to find
    bullet_best_seller_links = product_page.select(
        "div#detailBulletsWrapper_feature_div a[href*='/gp/bestsellers/']"
    )
    for index, best_seller_link in enumerate(bullet_best_seller_links):
        # the parent of the best seller link is the best seller bullet
        best_seller_widget = best_seller_link.parent
        # if there are more than one, for the first bullet, exclude other bullets inside it
        if len(bullet_best_seller_links) > 1 and index == 0:
            best_seller_rows.append(
                parse_bestseller_rank(product_id, best_seller_widget.contents[2], index)
            )
        else:
            best_seller_rows.append(
                parse_bestseller_rank(product_id, best_seller_widget, index)
            )

    ratings_widgets = product_page.select("span.cr-widget-TitleRatingsHistogram")
    if ratings_widgets:
        ratings_widget = only(ratings_widgets)
        average_ratings_widgets = ratings_widget.select(
            "span[data-hook='rating-out-of-text']"
        )
        if average_ratings_widgets:
            average_rating = float(
                re.fullmatch(
                    r"([\d\.\,]+) out of 5", only(average_ratings_widgets).text
                ).group(1)
            )
            number_of_ratings = int(
                re.fullmatch(
                    r"([\d,]+) global ratings?",
                    remove_commas(
                        only(
                            ratings_widget.select(
                                "[data-hook='total-review-count']",
                            )
                        ).text
                    ),
                ).group(1)
            )
            histogram_rows = ratings_widget.select("tr.a-histogram-row")
            if len(histogram_rows) != 5:
                raise NotFiveRows()

            five_star_text = get_star_percent(histogram_rows[0])
            four_star_percent = get_star_percent(histogram_rows[1])
            three_star_percent = get_star_percent(histogram_rows[2])
            two_star_percent = get_star_percent(histogram_rows[3])
            one_star_percent = get_star_percent(histogram_rows[4])

    fakespot_widgets = product_page.select("div.fakespot-main-grade-box-wrapper")
    if fakespot_widgets:
        fakespot_ranking = FAKESPOT_RANKINGS[
            only(product_page.select("div#fs-letter-grade-box")).text
        ]

    new_seller_widgets = product_page.select("div#fakespot-badge")
    if new_seller_widgets:
        only(new_seller_widgets)
        new_seller = True

    # box on the right where you buy the product
    # sometimes there is multiple buyboxes for different options
    buybox_sets = product_page.select("#buyBoxAccordion > div[id*='AccordionRow']")
    if buybox_sets:
        # use the first buybox
        buybox = buybox_sets[0]
        (
            free_prime_shipping,
            free_returns,
            limited_stock,
            out_of_stock,
            price,
            primary_shipping_conditional,
            primary_shipping_cost,
            primary_shipping_date_start,
            primary_shipping_date_end,
            return_within_days,
            secondary_shipping_date_start,
            secondary_shipping_date_end,
            ships_from_amazon,
            sold_by_amazon,
            undeliverable,
            unit_price,
            unit,
        ) = parse_buybox(buybox, current_year)
    else:
        buyboxes = product_page.select(
            "div[data-csa-c-content-id='desktop_buybox_group_1']"
        )
        if buyboxes:
            buybox = only(buyboxes)
            (
                free_prime_shipping,
                free_returns,
                limited_stock,
                out_of_stock,
                price,
                primary_shipping_conditional,
                primary_shipping_cost,
                primary_shipping_date_start,
                primary_shipping_date_end,
                return_within_days,
                secondary_shipping_date_start,
                secondary_shipping_date_end,
                ships_from_amazon,
                sold_by_amazon,
                undeliverable,
                unit_price,
                unit,
            ) = parse_buybox(buybox, current_year)

    subscription_widgets = product_page.select("div#snsAccordionRowMiddle")
    if subscription_widgets:
        subscription_available = True

    # if no list price, assume the list price is the price
    if list_price is None:
        list_price = price
    # if no unit price, the unit is "purchase" and the unit price is the price
    if unit_price is None:
        unit_price = price
    # convert coupon percents to a coupon amount
    if not (coupon_percent is None or price is None):
        coupon_amount = coupon_percent / 100 * price
    # if no end date, the date range is 0, and the end date is the start date
    if primary_shipping_date_end is None:
        primary_shipping_date_end = primary_shipping_date_start
    if secondary_shipping_date_end is None:
        secondary_shipping_date_start = secondary_shipping_date_end

    product_rows.append(
        DataFrame(
            {
                "answered_questions": answered_questions,
                "amazons_choice": amazons_choice,
                "average_rating": average_rating,
                "climate_friendly": climate_friendly,
                "coupon_amount": coupon_amount,
                "fakespot_ranking": fakespot_ranking,
                "free_prime_shipping": free_prime_shipping,
                "free_returns": free_returns,
                "hidden_prices": hidden_prices,
                "limited_stock": limited_stock,
                "list_price": list_price,
                "product_id": product_id,
                "new_seller": new_seller,
                "non_returnable_text": non_returnable_text,
                "number_of_ratings": number_of_ratings,
                "out_of_stock": out_of_stock,
                "price": price,
                "primary_shipping_cost": primary_shipping_cost,
                "primary_shipping_conditional": primary_shipping_conditional,
                "primary_shipping_date_start": primary_shipping_date_start,
                "primary_shipping_date_end": primary_shipping_date_end,
                "product_department": product_department,
                "refurbished": refurbished,
                "return_within_days": return_within_days,
                "secondary_shipping_date_start": secondary_shipping_date_start,
                "secondary_shipping_date_end": secondary_shipping_date_end,
                "ships_from_amazon": ships_from_amazon,
                "small_business": small_business,
                "sold_by_amazon": sold_by_amazon,
                "subscribe_coupon": subscribe_coupon,
                "subscription_available": subscription_available,
                "undeliverable": undeliverable,
                "unit": unit,
                "unit_price": unit_price,
                "used_only": used_only,
                "one_star_percent": one_star_percent,
                "two_star_percent": two_star_percent,
                "three_star_percent": three_star_percent,
                "four_star_percent": four_star_percent,
                "five_star_text": five_star_text,
            },
            index=[0],
        ).set_index("product_id")
    )


def parse_product_pages(
    search_results_data, product_pages_folder, product_logs_folder, current_year
):
    product_rows = []
    category_rows = []
    best_seller_rows = []
    for product_id in get_filenames(product_pages_folder):
        try:
            parse_product_page(
                product_rows,
                best_seller_rows,
                category_rows,
                product_pages_folder,
                product_id,
                current_year,
            )
        except Exception as exception:
            webbrowser.open(path.join(product_pages_folder, product_id + ".html"))
            raise exception

    return (
        # take the rearch results data
        search_results_data.set_index("product_id")
        .join(
            # add in product data
            concat(product_rows),
            how="left",
        )
        .join(
            # add in product logs
            combine_folder_csvs(product_logs_folder, "product_id"),
            how="left",
        ),
        concat(category_rows, ignore_index=True),
        concat(best_seller_rows, ignore_index=True),
    )
