from os import path
from pandas import concat, DataFrame
import re
from src.utilities import get_filenames, only, read_html
import webbrowser
from datetime import date

# e.g. 1,000 -> 1000
def remove_commas(a_string):
    return a_string.replace(",", "")


def get_price(price_text):
    return float(remove_commas(re.fullmatch(r"\$(.*)", price_text).group(1)))


def get_star_percentage(histogram_row):
    return re.fullmatch(
        "(.*)%", only(histogram_row.select(".a-text-right > .a-size-base")).text.strip()
    ).group(1)


class NotFiveRows(Exception):
    pass


class NotUnsupported(Exception):
    pass


class NotOneOrTwoPrices(Exception):
    pass


class NotFreePrime(Exception):
    pass


class NotFreeDelivery(Exception):
    pass


class UnrecognizedDate(Exception):
    pass


FAKESPOT_RANKINGS = {"A": 1, "B": 2, "C": 3, "D": 4, "F": 5, "?": None}

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

def parse_date(date_text, current_year):
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

    single_month_match = re.search(r"(\w+) (\d+) \- (\d+)", date_text)
    if not single_month_match is None:
        month_number = MONTH_NUMBERS[single_month_match.group(1)]
        return date(current_year, month_number, int(single_month_match.group(2))), date(
            current_year, month_number, int(single_month_match.group(3))
        )

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

    raise UnrecognizedDate(date_text)

def parse_bestseller_rank(product_filename, best_seller_widget, index):
    match = re.search(
        r"#(\d+)\s+in\s+([^\(]*)", best_seller_widget.text.strip()
    )
    return DataFrame(
        {
            "order": index + 1,
            "product_filename": product_filename,
            "best_seller_rank": int(remove_commas(match.group(1))),
            "best_seller_category": match.group(2).strip(),
        },
        index=[0],
    )


def parse_product_page(
    product_rows,
    best_seller_rows,
    category_rows,
    product_pages_folder,
    product_filename,
    current_year=2023,
):
    product_page = read_html(path.join(product_pages_folder, product_filename + ".html"))

    # return without doing anything for a variety of non-standard product pages
    unsupported_browser_widgets = product_page.select("h2.heading.title")
    if unsupported_browser_widgets:
        if (
            only(unsupported_browser_widgets).text.strip()
            != "Your browser is not supported"
        ):
            raise NotUnsupported()
        return

    consider_alternative_widgets = product_page.select("div#percolate-ui-lpo_div")
    if consider_alternative_widgets:
        only(consider_alternative_widgets)
        return

    product_type_widgets = product_page.select("div#dp")
    if product_type_widgets:
        return

    product_type = only(product_type_widgets)["class"][0]
    if (
        product_type == "book"
        or product_type == "ebooks"
        or product_type == "digitaltextfeeds"
        or product_type == "digital_software"
        or product_type == "device-type-desktop"
        or product_type == "audible"
        or product_type == "swa_physical"
    ):
        return

    used_only_widgets = product_page.select("div#usedOnlyBuybox")
    if used_only_widgets:
        only(used_only_widgets)
        return

    refurbished_options = product_page.select(
        "div#buyBoxAccordion > div[id*='renewed']"
    )
    if refurbished_options:
        return

    amazons_choice = False
    average_rating = None
    climate_friendly = False
    conditional_shipping = False
    coupon_percent = None
    fakespot_rank = None
    free_returns = False
    free_prime_shipping = False
    hidden_prices = False
    list_price = None
    more_on_the_way = False
    new_seller = False
    number_left_in_stock = None
    number_of_answered_questions = None
    number_of_formats = 1
    number_of_ratings = None
    out_of_stock = False
    over_a_thousand_answered_questions = False
    price = None
    primary_delivery_start_date = None
    primary_delivery_end_date = None
    primary_shipping_cost = None
    returnable = True
    return_until_days = None
    secondary_delivery_start_date = None
    secondary_delivery_end_date = None
    ships_from_amazon = False
    small_business = False
    sold_by_amazon = None
    subscription_available = False
    subscribe_coupon_percent = None
    undeliverable = False
    unit = ""
    unit_price = None    

    one_star_percentage = None
    two_star_percentage = None
    three_star_percentage = None
    four_star_percentage = None
    five_star_percentage = None

    for index, category_widget in enumerate(
        product_page.select("div#wayfinding-breadcrumbs_feature_div a")
    ):
        category_rows.append(
            DataFrame(
                {
                    "order": index + 1,
                    "category": category_widget.text.strip(),
                    "product_filename": product_filename,
                },
                index=[0],
            )
        )

    answered_questions_widgets = product_page.select("a#askATFLink")
    if answered_questions_widgets:
        answered_questions_text = re.fullmatch(
            "(.*) answered questions?", only(answered_questions_widgets).text.strip()
        ).group(1)
        if answered_questions_text == "1000+":
            over_a_thousand_answered_questions = True
        else:
            number_of_answered_questions = int(answered_questions_text)

    amazons_choice_widgets = product_page.select("acBadge_feature_div")
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

    center_priceboxes_containers = product_page.select("div#apex_desktop")
    if center_priceboxes_containers:
        center_priceboxes_container = only(center_priceboxes_containers)
        center_priceboxes = center_priceboxes_container.select(
            "div.offersConsistencyEnabled > div[style='']"
        )
        if len(center_priceboxes) > 0:
            center_pricebox = center_priceboxes[0]
        else:
            center_pricebox = center_priceboxes_container
        list_price_widgets = center_pricebox.select(
            "span.a-price[data-a-strike='true'] span.a-offscreen"
        )
        if len(list_price_widgets) > 0:
            list_price = get_price(only(list_price_widgets).text.strip())

    promo_widget_containers = product_page.select("#promoPriceBlockMessage_feature_div")
    if promo_widget_containers:
        promo_widget_container = only(promo_widget_containers)
        promo_widgets = promo_widget_container.select(
            "div.offersConsistencyEnabled > div[style='']"
        )
        if promo_widgets:
            promo_widget = promo_widgets[0]
        else:
            promo_widget = promo_widget_container

        coupon_widgets = promo_widget.select("label[id*='couponText']")
        if coupon_widgets:
            coupon_text = only(coupon_widgets).text.strip()
            coupon_match = re.search(r"Apply (.*)% coupon", coupon_text)
            if not coupon_match is None:
                coupon_percent = int(coupon_match.group(1))
            subscribe_coupon_match = re.search(
                r"Save (.*)%.*Subscribe & Save", coupon_text
            )
            if not subscribe_coupon_match is None:
                subscribe_coupon_percent = int(subscribe_coupon_match.group(1))

    hidden_price_widgets = product_page.select(
        "a[href='/forum/where%20is%20the%20price']"
    )
    if hidden_price_widgets:
        only(hidden_price_widgets)
        hidden_prices = True
    
    for index, best_seller_link in enumerate(
        product_page.select("div#prodDetails a[href*='/gp/bestsellers']")
    ):
        best_seller_rows.append(
            parse_bestseller_rank(product_filename, best_seller_link.parent, index)
        )

    best_seller_bullets = product_page.select(
        "div#detailBulletsWrapper_feature_div a[href*='/gp/bestsellers/']"
    )

    for index, best_seller_link in enumerate(best_seller_bullets):
        if len(best_seller_bullets) > 1 and index == 0:
            best_seller_rows.append(
                parse_bestseller_rank(
                    product_filename, best_seller_link.parent.contents[2], index
                )
            )
        else:
            best_seller_rows.append(
                parse_bestseller_rank(product_filename, best_seller_link.parent, index)
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
                    r"(.*) out of 5", only(average_ratings_widgets).text.strip()
                ).group(1)
            )
            number_of_ratings = int(
                remove_commas(
                    re.fullmatch(
                        r"(.*) global ratings?",
                        only(
                            ratings_widget.select(
                                "[data-hook='total-review-count']",
                            )
                        ).text.strip(),
                    ).group(1)
                )
            )
            histogram_rows = ratings_widget.select(".a-histogram-row")
            if len(histogram_rows) != 5:
                raise NotFiveRows()

            five_star_percentage = get_star_percentage(histogram_rows[0])
            four_star_percentage = get_star_percentage(histogram_rows[1])
            three_star_percentage = get_star_percentage(histogram_rows[2])
            two_star_percentage = get_star_percentage(histogram_rows[3])
            one_star_percentage = get_star_percentage(histogram_rows[4])
    
    fakespot_widgets = product_page.select("div.fakespot-main-grade-box-wrapper")
    if fakespot_widgets:
        fakespot_rank = FAKESPOT_RANKINGS[
            only(product_page.select("div#fs-letter-grade-box")).text.strip()
        ]
    
    new_seller_widgets = product_page.select("div#fakespot-badge")
    if new_seller_widgets:
        only(new_seller_widgets)
        new_seller = True

    accordion_rows = product_page.select("#buyBoxAccordion > div[id*='AccordionRow']")
    if accordion_rows:
        number_of_formats = len(accordion_rows)
        buybox = accordion_rows[0]
    else:
        buybox = only(
            product_page.select("div[data-csa-c-content-id='desktop_buybox_group_1']")
        )

    out_of_stock_widgets = buybox.select("div#outOfStock")
    if out_of_stock_widgets:
        only(out_of_stock_widgets)
        out_of_stock = True

    undeliverable_widgets = buybox.select("div#exports_desktop_undeliverable_buybox")
    if undeliverable_widgets:
        only(undeliverable_widgets)
        undeliverable = True

    price_pair_widgets = buybox.select("div#corePrice_feature_div")
    if price_pair_widgets:
        price_pair_widget = only(price_pair_widgets)
        price_widgets = price_pair_widget.select("span.a-offscreen")
        if len(price_widgets) == 0:
            pass
        elif len(price_widgets) == 1:
            price = get_price(price_widgets[0].text.strip())
        elif len(price_widgets) == 2:
            price = get_price(price_widgets[0].text.strip())
            unit_price = get_price(price_widgets[0].text.strip())
            unit = (
                re.search(r"\/(.*)\)", price_pair_widget.text.strip()).group(1).strip()
            )
        else:
            raise NotOneOrTwoPrices()

    prime_promotion_widgets = buybox.select("#price-shipping-message")
    if prime_promotion_widgets:
        shipping_message = only(prime_promotion_widgets).text.strip()
        if shipping_message == "Get Fast, Free Shipping with Amazon Prime":
            free_prime_shipping = True

    import_widgets = buybox.select(
        "#desktop_qualifiedBuyBox #amazonGlobal_feature_div > .a-color-secondary"
    )
    if import_widgets:
        primary_shipping_cost = re.search(
            r"\$(.*) Shipping", only(import_widgets).text
        ).group(1)

    availability_widgets = buybox.select("div#availability")
    if availability_widgets:
        availability = only(availability_widgets).text.strip()
        left_in_stock_match = re.search(r"Only (.*) left in stock", availability)
        if not (left_in_stock_match is None):
            number_left_in_stock = int(remove_commas(left_in_stock_match.group(1)))
        more_on_the_way_match = re.search(r"more on the way", availability)
        if not (more_on_the_way_match is None):
            more_on_the_way = True
        out_of_stock_match = re.search(r"Temporarily out of stock", availability)
        if not (out_of_stock_match is None):
            out_of_stock = True

    non_returnable_widgets = product_page.select(
        "div#dsvReturnPolicyMessage_feature_div"
    )
    if non_returnable_widgets:
        returnable = False

    returns_widgets = buybox.select("a#creturns-policy-anchor-text")
    if returns_widgets:
        free_returns = True

    primary_delivery_widgets = buybox.select(
        "div#mir-layout-DELIVERY_BLOCK-slot-PRIMARY_DELIVERY_MESSAGE_LARGE > span[data-csa-c-content-id*='DEXUnified']"
    )
    if primary_delivery_widgets:
        primary_delivery_widget = only(primary_delivery_widgets)
        primary_shipping_text = primary_delivery_widget.text.strip()
        primary_shipping_cost_match = re.search(
            "([^ ]*).*delivery", primary_shipping_text
        )
        if not primary_shipping_cost_match is None:
            primary_shipping_cost_text = primary_shipping_cost_match.group(1)
            if primary_shipping_cost_text == "FREE":
                primary_shipping_cost = 0
            else:
                primary_shipping_cost = get_price(primary_shipping_cost_text)

        if not re.search(r"on orders shipped by Amazon over", primary_shipping_text):
            conditional_shipping = True

        primary_delivery_start_date, primary_delivery_end_date = parse_date(
            primary_delivery_widget["data-csa-c-delivery-time"], current_year
        )

    secondary_delivery_widgets = buybox.select(
        "div#mir-layout-DELIVERY_BLOCK-slot-SECONDARY_DELIVERY_MESSAGE_LARGE > span[data-csa-c-content-id*='DEXUnified']"
    )
    if secondary_delivery_widgets:
        secondary_delivery_widget = only(secondary_delivery_widgets)
        secondary_delivery_start_date, secondary_delivery_end_date = parse_date(
            secondary_delivery_widget["data-csa-c-delivery-time"], current_year
        )

    ships_from_widgets = buybox.select(
        "div.tabular-buybox-text[tabular-attribute-name='Ships from']"
    )
    if ships_from_widgets:
        ships_from_amazon = (
            not re.search(r"Amazon", only(ships_from_widgets).text.strip()) is None
        )

    sold_by_widgets = buybox.select(
        "div.tabular-buybox-text[tabular-attribute-name='Sold by']"
    )
    if sold_by_widgets:
        sold_by_amazon = (
            not re.search(r"Amazon", only(sold_by_widgets).text.strip()) is None
        )
    
    returns_text_widgets = buybox.select(
        "div.tabular-buybox-text[tabular-attribute-name='Returns'] span.tabular-buybox-text-message"
    )
    if returns_text_widgets:
        return_timeline_match = re.search(
            r"within (.*) days", only(returns_text_widgets).text.strip()
        )
        if not return_timeline_match is None:
            return_until_days = int(return_timeline_match.group(1))

    subscription_widgets = product_page.select("div#snsAccordionRowMiddle")
    if subscription_widgets:
        subscription_available = True
    
    product_rows.append(
        DataFrame({
            "amazons_choice": amazons_choice,
            "average_rating": average_rating,
            "climate_friendly": climate_friendly,
            "conditional_shipping": conditional_shipping,
            "coupon_percent": coupon_percent,
            "fakespot_rank": fakespot_rank,
            "free_returns": free_returns,
            "free_prime_shipping": free_prime_shipping,
            "hidden_prices": hidden_prices,
            "list_price": list_price,
            "more_on_the_way": more_on_the_way,
            "new_seller": new_seller,
            "number_left_in_stock": number_left_in_stock,
            "number_of_answered_questions": number_of_answered_questions,
            "number_of_formats": number_of_formats,
            "number_of_ratings": number_of_ratings,
            "out_of_stock": out_of_stock,
            "over_a_thousand_answered_questions": over_a_thousand_answered_questions,
            "price": price,
            "primary_delivery_start_date": primary_delivery_start_date,
            "primary_delivery_end_date": primary_delivery_end_date,
            "primary_shipping_cost": primary_shipping_cost,
            "returnable": returnable,
            "return_until_days": return_until_days,
            "secondary_delivery_start_date": secondary_delivery_start_date,
            "secondary_delivery_end_date": secondary_delivery_end_date,
            "ships_from_amazon": ships_from_amazon,
            "small_business": small_business,
            "sold_by_amazon": sold_by_amazon,
            "subscription_available": subscription_available,
            "subscribe_coupon_percent": subscribe_coupon_percent,
            "undeliverable": undeliverable,
            "unit": unit,
            "unit_price": unit_price,

            "one_star_percentage": one_star_percentage,
            "two_star_percentage": two_star_percentage,
            "three_star_percentage": three_star_percentage,
            "four_star_percentage": four_star_percentage,
            "five_star_percentage": five_star_percentage,
            },
            index=[0],
        )
    )


def parse_product_pages(
    product_pages_folder,
    product_results_file,
    best_seller_results_file,
    category_results_file,
    max_products=10**6,
):
    product_rows = []
    best_seller_rows = []
    category_rows = []
    for index, product_filename in enumerate(get_filenames(product_pages_folder)):
        if index >= max_products:
            break

        print(product_filename)
        # all digits
        if not (re.fullmatch(r".*\-sellers", product_filename) is None):
            continue

        try:
            parse_product_page(
                product_rows,
                best_seller_rows,
                category_rows,
                product_pages_folder,
                product_filename,
            )
        except Exception as exception:
            webbrowser.open(path.join(product_pages_folder, product_filename + ".html"))
            sellers_file = path.join(
                product_pages_folder, product_filename + "-sellers.html"
            )
            if path.isfile(sellers_file):
                webbrowser.open(sellers_file)
            raise exception

    concat(product_rows, ignore_index=True).to_csv(product_results_file, index=False)
    concat(best_seller_rows, ignore_index=True).to_csv(
        best_seller_results_file, index=False
    )
    concat(category_rows, ignore_index=True).to_csv(category_results_file, index=False)


# TODO:
# protection plans
# number of variations
# more categories
