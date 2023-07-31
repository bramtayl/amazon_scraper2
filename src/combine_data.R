# I scraped the following variables from Amazon product pages:

# - `ASIN`: Amazon's ID for the product.
# - `answered_questions`: The number of answered questions. Amazon reports "1000+" if there are more than 1000 answers, in which case, I defaulted to 1000.
# - `amazons_choice`: Whether the product is an Amazon's choice product.
# - `average_rating`: The average rating of the product, between 0 and 5, for example, 3.5 out of 5 stars.
# - `best_seller_category`: Amazon chooses a handful of categories containing the product and reports the best-seller rank within each (see `category` below). I used the most general category listed with a best seller rank. 
# - `best_seller_rank`: The product's rank within its `best_seller_category`, for example, #64 in Watches
# - `category`: Amazon categorizes products into a nested tree, with more general categories containing more specific categories. I used the most general category listed.
# - `climate_friendly`: Whether the product has the `climate_friendly_badge`
# - `coupon_amount`: The coupon amount, in dollars, if a coupon is available, or 0 if no coupon is available.
# - `fakespot_ranking`: Fakespot provides the following rankings, based on the amount of fake reviews a product has: `A`, `B`, `C`, `D`, and `F`. Fakespot only reports rankings for products with enough reviews to calculate a ranking.
# - `free_prime_shipping`: Whether shipping is free with Amazon Prime.
# - `free_returns`: Whether returning the product is free.
# - `limited_stock`: Whether there is a limited stock of the item.
# - `list_price`: The original price of the item, before any discounts (but not coupons).
# - `new_seller`: Whether the seller only recently started selling, as reported by Fakespot.
# - `number_of_ratings`: The number of ratings.
# - `price`: The price of the item, after any discounts  (but not coupons).
# - `department`: The department of the product. Departments are similar to categories, but there is a smaller number and they are not nested.
# - `rush_shipping_available`: Whether rush shipping is available.
# - `ships_from_amazon`: Whether Amazon handles product shipping.
# - `small_business`: Whether the seller has a small business badge.
# - `sold_by_amazon`: Whether Amazon decides the price of the product.
# - `standard_shipping_cost`: The cost for standard shipping.
# - `standard_shipping_conditional`: Whether standard shipping is free only with a subscription.
# - `standard_shipping_date_start`: The earliest arrival date
# - `standard_shipping_date_end`: The latest arrival date.
# - `subscribe_coupon`: Whether a coupon is available if you subscribe.
# - `subscription_available`: Whether you can subscribe to receive a product, for example, receive a shipment each month.
# - `unit`: The units of the product, for example, ounces, or "purchase" if no unit is provided.
# - `unit_price`: The price per unit of the product, or just price if there are no units.
# - `one_star_percent`: The percentage of one-star reviews.
# - `two_star_percent`: The percentage of two-star reviews.
# - `three_star_percent`: The percentage of three-star reviews.
# - `four_star_percent`: The percentage of four-star reviews.
# - `five_star_percent`: The percentage of five-star reviews.

# I excluded these categories from searches:
# - Digital_Software
# - Digital_Video_Download
# - Digital_Video_Games
# - Digital_Ebook_Purchase
# - Digital_Musis_Purchase

# ```{r}
library(ggplot2)
library(timechange) # needed for lubridate
library(lubridate, warn.conflicts = FALSE)
library(pander)
library(purrr)
library(readr)
library(stringi)
library(tidyr)
library(zoo, warn.conflicts = FALSE)
# load last for select
library(dplyr, warn.conflicts = FALSE)

search_data <-
    read_csv("results/search_data.csv", show_col_types = FALSE) %>%
    arrange(query, page_number, rank) %>%
    # if there are multiple sponsored listings, use the first one
    # same with unsponsored listings
    group_by(query, ASIN, sponsored) %>%
    slice(1) %>%
    ungroup %>%
    # rerank over all pages
    arrange(query, page_number, rank) %>%
    group_by(query) %>%
    mutate(search_rank = seq_len(n())) %>%
    ungroup() %>%
    select(-page_number, -rank) %>%
    # reverse the order for the locf
    arrange(query, desc(search_rank)) %>%
    group_by(query) %>%
    mutate(
        # locf the unsponsored listings
        next_unsponsored_ASIN = 
            na.locf(ifelse(sponsored, NA, ASIN), na.rm = FALSE)
    ) %>%
    ungroup() %>%
    # return to forward ordering
    arrange(query, search_rank)

log_data <- list_rbind(map(
    list.files("results/product_pages"),
    function(file_name) {
        modification_time = 
        tibble(
            ASIN = stri_split_fixed(file_name, ".")[[1]][1],
            modification_date_time = 
            file.info(
                file.path("results/product_pages", file_name)
            )$mtime
        )
    }
))

product_data <- 
    search_data %>%
    left_join(
        read_csv("results/product_data.csv", show_col_types = FALSE) %>%
        mutate(
            # NA for 0 or negative prices
            log_unit_price = ifelse(unit_price > 0, log(unit_price), NA),
            discount_percent = (list_price - price) / price,
            coupon_percent = coupon_amount / price,
            negative_log_best_seller_rank = -log(best_seller_rank)
        ),
        by = "ASIN"
    ) %>%
    left_join(
        log_data,
        by = "ASIN"
    ) %>%
    left_join(
        read_csv(
            "results/relevance_data.csv",
            show_col_types = FALSE
        ) %>%
            # normalize this for easier interpretation
            mutate(scaled_relevance_score = (score - mean(score)) / sd(score)),
        by = c("ASIN", "query")
    ) %>%
    mutate(
        floor_modification_date_time = 
            floor_date(modification_date_time, unit = "days"),
        time_of_day = modification_date_time - floor_modification_date_time,
        modification_date = as.Date(floor_modification_date_time, tz = "BST"),
        standard_shipping_range = 
            standard_shipping_date_end - standard_shipping_date_start,
        standard_expected_shipping_days = 
            standard_shipping_date_start - modification_date + 
            standard_shipping_range / 2,
        negative_log_best_seller_rank = -log(best_seller_rank)
    )

rerank <- function(data) {
    data %>%
    arrange(query, search_rank) %>%
    group_by(query) %>%
    mutate(
        search_rank = seq_len(n())
    ) %>%
    ungroup()
}

complete_data <-
    product_data %>%
    select(
        ASIN,
        amazon_brand,
        amazons_choice,
        answered_questions,
        average_rating,
        best_seller_category,
        category,
        climate_friendly,
        search_rank,
        coupon_percent,
        department,
        discount_percent,
        fakespot_ranking,
        free_prime_shipping,
        free_returns,
        limited_stock,
        log_unit_price,
        negative_log_best_seller_rank,
        new_seller,
        number_of_ratings,
        query,
        returns,
        scaled_relevance_score,
        ships_from_amazon,
        small_business,
        sold_by_amazon,
        sponsored,
        standard_expected_shipping_days,
        standard_shipping_range,
        subscribe_coupon,
        subscription_available,
        time_of_day,
        unit,
        one_star_percent,
        two_star_percent,
        three_star_percent,
        four_star_percent,
        five_star_percent
    ) %>%
    filter(complete.cases(.) & !sponsored) %>%
    rerank()

model <- glm(
    search_rank ~
    amazon_brand + 
    amazons_choice + 
    answered_questions +
    average_rating +
    best_seller_category +
    category +
    climate_friendly +
    coupon_percent +
    department +
    discount_percent +
    factor(fakespot_ranking) +
    free_prime_shipping +
    free_returns +
    limited_stock +
    log_unit_price +
    negative_log_best_seller_rank +
    new_seller +
    number_of_ratings +
    query +
    returns +
    scaled_relevance_score +
    ships_from_amazon +
    small_business +
    sold_by_amazon +
    standard_expected_shipping_days +
    standard_shipping_range +
    subscribe_coupon +
    subscription_available +
    time_of_day +
    unit +
    one_star_percent +
    two_star_percent +
    four_star_percent +
    five_star_percent,
    family = "poisson",
    data = complete_data
)

confint.default(model)["scaled_relevance_score",]

relevance_coefficient <- coef(model)[["scaled_relevance_score"]]

exp_relevance_coefficient <- exp(relevance_coefficient)

duplicates_data <-
    read_csv("results/duplicates_data.csv", show_col_types = FALSE) %>%
    arrange(query, page_number, rank) %>%
    # if there are multiple sponsored listings, use the first one
    # same with unsponsored listings
    group_by(query, ASIN, sponsored) %>%
    slice(1) %>%
    ungroup %>%
    # rerank over all pages
    arrange(query, page_number, rank) %>%
    group_by(query) %>%
    mutate(search_rank = seq_len(n())) %>%
    ungroup() %>%
    select(-page_number, -rank) %>%
    # reverse the order for the locf
    arrange(query, desc(search_rank)) %>%
    group_by(query) %>%
    mutate(
        # locf the unsponsored listings
        next_unsponsored_ASIN = 
            na.locf(ifelse(sponsored, NA, ASIN), na.rm = FALSE)
    ) %>%
    ungroup() %>%
    # return to forward ordering
    arrange(query, search_rank)


unsponsored_data <-
    duplicates_data %>%
    select(query, ASIN, search_rank, sponsored) %>%
    filter(!sponsored) %>%
    rerank %>%
    rename(unsponsored_rank = search_rank)

sponsored_data <-
    duplicates_data %>%
    select(query, ASIN, search_rank, sponsored) %>%
    pivot_wider(names_from = sponsored, values_from = search_rank) %>%
    rename(
        unsponsored_combined_rank = `FALSE`,
        sponsored_combined_rank = `TRUE`
    ) %>%
    filter(!is.na(sponsored_combined_rank)) %>%
    left_join(
        duplicates_data %>%
        filter(sponsored) %>%
        select(
            query,
            ASIN,
            displaced_ASIN = next_unsponsored_ASIN
        ),
        by = c("query", "ASIN")
    ) %>%
    left_join(
        unsponsored_data %>%
        select(
            query,
            ASIN,
            unsponsored_rank
        ),
        by = c("query", "ASIN")
    ) %>%
    # use displaced ASIN to find the displaced rank
    left_join(
        unsponsored_data %>%
        select(
            query,
            displaced_ASIN = ASIN,
            displaced_unsponsored_rank = unsponsored_rank
        ),
        by = c("query", "displaced_ASIN")
    ) %>%
    mutate(
        relevance_boost = 
            (log(displaced_unsponsored_rank) - log(unsponsored_rank)) /
            relevance_coefficient
    )

percent_present <- function(vector) {
    sum(!is.na(vector)) / length(vector) * 100
}

sum(!is.na(sponsored_data$unsponsored_rank))
with(
    sponsored_data,
    percent_present(unsponsored_rank)
)

with(
    sponsored_data %>%
        filter(!is.na(unsponsored_rank)),
    boxplot(relevance_boost,
        ylab = "Relevance score boost equivalent, in standard deviations",
        main = "Sponsorship boosts, for duplicated sponsored products"
    )
)
