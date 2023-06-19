from os import path
from pandas import concat, DataFrame
import re
from src.utilities import (
    get_filenames,
    only,
    read_html,
    strict_match,
)
import webbrowser
from datetime import date

# convert fakespot grades to a numerical rank
# this is still ordinal, not cardinal
FAKESPOT_RANKINGS = {"A": 1, "B": 2, "C": 3, "D": 4, "F": 5, "?": None}


def get_star_percent(histogram_row):
    return int(
        strict_match(
            r"(\d)+%", only(histogram_row.select("td.a-text-right")).text
        ).group(1)
    )


# error if there aren't rows for each of 1-5 stars
class NotFiveRows(Exception):
    pass


# error if we misidentify an unsupported browser pages
class NotUnsupported(Exception):
    pass


# there should be either just one price, or a price and a unit price
class NotOneOrTwoPrices(Exception):
    pass


def remove_commas(a_string):
    return a_string.replace(",", "")


def parse_price(price_text):
    # dollar sign, then digits and decimal
    return float(strict_match(r"\$([\d\.]+)", remove_commas(price_text)).group(1))


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


# product_id = "Fossil-Quartz-Stainless-Steel-ChronographdpB009LSKPYIrefsr_1_51keywordswatchesformenqid1684247239sr8-51"
# product_page = read_html(path.join(product_pages_folder, product_id + ".html"))
# best_seller_link = product_page.select("div#detailBulletsWrapper_feature_div a[href*='/gp/bestsellers/']")[0]
def parse_best_seller_link(
    best_seller_link, skip_header=False
):
    if skip_header:
        content_index = 1
    else:
        content_index = 0

    # the parent of the best seller link is the best seller widget
    best_seller_widget = best_seller_link.parent

    if "See Top 100 in" in best_seller_widget.text:
        # e.g. #1 in Category (See Top 100 in [Category](url))
        # or #1 Free in Kindle Store (See Top 100 in [Kindle Store](url))
        match = strict_match(
            r"#([\d,]+) (?:Free )?in (.*) \(",
            best_seller_widget.contents[content_index].text,
        )
        rank_text = match.group(1)
        category_text = match.group(2)
    else:
        # e.g. #1 in [Category](url)
        rank_text = strict_match(
            r"#([\d,]+) (?:Free )?in",
            best_seller_widget.contents[content_index].text,
        ).group(1)
        category_text = best_seller_link.text

    return category_text.strip(), int(remove_commas(rank_text))


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
    return_within_days = 0
    returns_text = ""
    rush_shipping_date_start = None
    rush_shipping_date_end = None
    ships_from_amazon = False
    sold_by_amazon = False
    standard_shipping_conditional = False
    standard_shipping_cost = None
    standard_shipping_date_start = None
    standard_shipping_date_end = None
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
            unit_price_widget = price_widgets[1]
            unit_price = parse_price(unit_price_widget.text)
            unit = (
                strict_match(
                    # e.g "/ Fl Oz )"
                    r"\/(.*)\)",
                    # parent the price and offscreen price
                    # parent of that includes the unit
                    # first paren is child 0, price is child 1, unit and close paren is child 2
                    unit_price_widget.parent.parent.contents[2].text
                )
                .group(1)
                .strip()
            )

        if len(price_widgets) >= 3:
            raise NotOneOrTwoPrices()

    free_prime_shipping_widgets = buybox.select("span#price-shipping-message")
    if free_prime_shipping_widgets:
        free_prime_shipping = True

    availability_widgets = buybox.select(
        "div[data-csa-c-content-id='desktop_buybox_group_1'] div#availability > span:first-of-type"
    )
    if availability_widgets:
        if re.search(r"Only ([\d\,]+) left in stock", only(availability_widgets).text):
            limited_stock = True

    free_returns_widgets = buybox.select("a#creturns-policy-anchor-text")
    if free_returns_widgets:
        free_returns = True

    standard_shipping_widgets = buybox.select(
        "div#mir-layout-DELIVERY_BLOCK-slot-PRIMARY_DELIVERY_MESSAGE_LARGE > span[data-csa-c-content-id*='DEXUnified']"
    )
    if standard_shipping_widgets:
        standard_shipping_widget = only(standard_shipping_widgets)
        (standard_shipping_date_start, standard_shipping_date_end) = parse_dates(
            standard_shipping_widget["data-csa-c-delivery-time"], current_year
        )
        standard_shipping_cost_text = standard_shipping_widget[
            "data-csa-c-delivery-price"
        ]
        if standard_shipping_cost_text == "FREE":
            standard_shipping_cost = 0.0
        elif standard_shipping_cost_text != "":
            standard_shipping_cost = parse_price(standard_shipping_cost_text)
        if standard_shipping_widget["data-csa-c-delivery-condition"] != "":
            standard_shipping_conditional = True

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
                strict_match(
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
        return_within_days,
        rush_shipping_date_start,
        rush_shipping_date_end,
        ships_from_amazon,
        sold_by_amazon,
        standard_shipping_conditional,
        standard_shipping_cost,
        standard_shipping_date_start,
        standard_shipping_date_end,
        undeliverable,
        unit_price,
        unit,
    )

# product_rows = []
# product_id = get_filenames(product_pages_folder)[0]
def parse_product_page(
    product_rows,
    product_pages_folder,
    product_id,
    current_year,
):
    # add defaults for all our variables
    answered_questions = 0
    amazons_choice = False
    average_rating = None
    best_seller_category = ""
    best_seller_rank = None
    category = ""
    climate_friendly = False
    coupon_amount = None
    coupon_percent = None
    fakespot_ranking = None
    free_prime_shipping = False
    free_returns = False
    limited_stock = False
    list_price = None
    new_seller = False
    number_of_ratings = 0
    out_of_stock = False
    price = None
    refurbished = False
    return_within_days = 0
    rush_shipping_date_start = None
    rush_shipping_date_end = None
    ships_from_amazon = False
    small_business = False
    sold_by_amazon = None
    standard_shipping_conditional = False
    standard_shipping_cost = None
    standard_shipping_date_start = None
    standard_shipping_date_end = None
    subscription_available = False
    subscribe_coupon = False
    undeliverable = False
    unit = "Purchase"
    unit_price = None

    one_star_percent = None
    two_star_percent = None
    three_star_percent = None
    four_star_percent = None
    five_star_percent = None

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
    department_widgets = product_page.select("div#dp")
    if not department_widgets:
        return

    department = only(department_widgets)["class"][0]

    category_widgets = product_page.select("div#wayfinding-breadcrumbs_feature_div a")
    if category_widgets:
        # just get the broadest category
        category = category_widgets[0].text

    answered_questions_widgets = product_page.select("a#askATFLink span.a-size-base")
    if answered_questions_widgets:
        answered_questions_text = remove_commas(only(answered_questions_widgets).text)
        # won't show more than 1000
        if answered_questions_text == "1000+ answered questions":
            answered_questions = 1000
        else:
            answered_questions = int(
                strict_match(
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

    table_best_seller_links = product_page.select(
        "div#prodDetails a[href*='/gp/bestsellers']"
    )

    if len(table_best_seller_links) > 0:
        # table details
        best_seller_category, best_seller_rank = parse_best_seller_link(
            table_best_seller_links[0]
        )
    else:
        bullet_best_seller_links = product_page.select(
            "div#detailBulletsWrapper_feature_div a[href*='/gp/bestsellers/']"
        )
        if bullet_best_seller_links:
            best_seller_category, best_seller_rank = parse_best_seller_link(
                bullet_best_seller_links[0], True
            )

    ratings_widgets = product_page.select("span.cr-widget-TitleRatingsHistogram")
    if ratings_widgets:
        ratings_widget = only(ratings_widgets)
        average_ratings_widgets = ratings_widget.select(
            "span[data-hook='rating-out-of-text']"
        )
        if average_ratings_widgets:
            average_rating = float(
                strict_match(
                    r"([\d\.\,]+) out of 5", only(average_ratings_widgets).text
                ).group(1)
            )
            number_of_ratings = int(
                strict_match(
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

            five_star_percent = get_star_percent(histogram_rows[0])
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
            return_within_days,
            rush_shipping_date_start,
            rush_shipping_date_end,
            ships_from_amazon,
            sold_by_amazon,
            standard_shipping_conditional,
            standard_shipping_cost,
            standard_shipping_date_start,
            standard_shipping_date_end,
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
                return_within_days,
                rush_shipping_date_start,
                rush_shipping_date_end,
                ships_from_amazon,
                sold_by_amazon,
                standard_shipping_conditional,
                standard_shipping_cost,
                standard_shipping_date_start,
                standard_shipping_date_end,
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
    if coupon_amount is None:
        if not (coupon_percent is None or price is None):
            coupon_amount = coupon_percent / 100 * price
        else:
            coupon_amount = 0.0
    # if no end date, the date range is 0, and the end date is the start date
    if standard_shipping_date_end is None:
        standard_shipping_date_end = standard_shipping_date_start
    if rush_shipping_date_end is None:
        rush_shipping_date_start = rush_shipping_date_end

    product_rows.append(
        DataFrame(
            {
                "answered_questions": [answered_questions],
                "amazons_choice": [amazons_choice],
                "average_rating": [average_rating],
                "best_seller_rank": [best_seller_rank],
                "best_seller_category": [best_seller_category],
                "category": [category],
                "climate_friendly": [climate_friendly],
                "coupon_amount": [coupon_amount],
                "fakespot_ranking": [fakespot_ranking],
                "free_prime_shipping": [free_prime_shipping],
                "free_returns": [free_returns],
                "limited_stock": [limited_stock],
                "list_price": [list_price],
                "product_id": [product_id],
                "new_seller": [new_seller],
                "number_of_ratings": [number_of_ratings],
                "out_of_stock": [out_of_stock],
                "price": [price],
                "department": [department],
                "refurbished": [refurbished],
                "return_within_days": [return_within_days],
                "rush_shipping_date_start": [rush_shipping_date_start],
                "rush_shipping_date_end": [rush_shipping_date_end],
                "ships_from_amazon": [ships_from_amazon],
                "small_business": [small_business],
                "sold_by_amazon": [sold_by_amazon],
                "standard_shipping_cost": [standard_shipping_cost],
                "standard_shipping_conditional": [standard_shipping_conditional],
                "standard_shipping_date_start": [standard_shipping_date_start],
                "standard_shipping_date_end": [standard_shipping_date_end],
                "subscribe_coupon": [subscribe_coupon],
                "subscription_available": [subscription_available],
                "undeliverable": [undeliverable],
                "unit": [unit],
                "unit_price": [unit_price],
                "one_star_percent": [one_star_percent],
                "two_star_percent": [two_star_percent],
                "three_star_percent": [three_star_percent],
                "four_star_percent": [four_star_percent],
                "five_star_percent": [five_star_percent],
            },
        )
    )

# current_year = "CURRENT_YEAR"
def parse_product_pages(product_pages_folder, current_year):
    product_rows = []
    # product_id = get_filenames(product_pages_folder)[0]
    for product_id in get_filenames(product_pages_folder):
        try:
            parse_product_page(
                product_rows,
                product_pages_folder,
                product_id,
                current_year,
            )
        except Exception as exception:
            print("Error: ", product_id)
            webbrowser.open(path.join(product_pages_folder, product_id + ".html"))
            raise exception

    return concat(product_rows)
