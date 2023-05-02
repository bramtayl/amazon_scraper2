from bs4 import BeautifulSoup
from os import chdir, path
from pandas import concat, DataFrame
import re

FOLDER = "/home/brandon/amazon_scraper"
chdir(FOLDER)
from utilities import get_filenames, only


# index = 0
# file = open(path.join(search_pages_folder, search_id + ".html"), "r")
# search_result = BeautifulSoup(file, 'lxml').select("div.s-main-slot.s-result-list > div[data-component-type='s-search-result']")[index]
# file.close()
def parse_search_result(search_id, search_result, index):
    return DataFrame(
        {
            "search_id": search_id,
            "rank": index + 1,
            "url": only(
                search_result.select(
                    # a link in a heading
                    "h2 a",
                )
            )["href"],
        },
        # one row
        index=range(1),
    )

    # Comment everything else out for now because we only need the urls to save the products

    # sponsored_tags = search_result.select(
    #     ".puis-label-popover-default"
    # )
    # if len(sponsored_tags) > 0:
    #     # sanity check
    #     only(sponsored_tags)
    #     search_result_row["ad"] = True

    # limited_time_deal_label = search_result.select(
    #     "span[data-a-badge-color='sx-lighting-deal-red']"
    # )

    # if limited_time_deal_label is not None:
    #     only(limited_time_deal_label)
    #     search_result_row["limited_time_deal"] = True

    # provenance_certifications = search_result.select(
    #     By.XPATH, "//*[contains(@data-s-pc-popover, 'provenanceCertifications')]"
    # )
    # if len(provenance_certifications) > 0:
    #     search_result_row["provenance_certifications"] = provenance_certifications.text.strip()

    # images = search_result.select(
    #     "img[class='s-image']"
    # )
    # for image in images:
    #     if image.get_attribute("src") == "https://m.media-amazon.com/images/I/111mHoVK0kL._SS200_.png":
    #         search_result_row["small_business"] = True

    # return search_result_row


# search_id = "All Departments-dog food"
def parse_search_page(search_pages_folder, search_id):
    with open(path.join(search_pages_folder, search_id + ".html"), "r") as file:
        return concat(
            (
                parse_search_result(search_id, search_result, index)
                for index, search_result in enumerate(
                    BeautifulSoup(file, "lxml").select(
                        "div.s-main-slot.s-result-list > div[data-component-type='s-search-result']",
                    )
                )
            ),
            ignore_index=True,
        )


def parse_search_pages(search_pages_folder):
    return concat(
        (
            parse_search_page(search_pages_folder, search_id)
            for search_id in get_filenames(search_pages_folder)
        ),
        ignore_index=True,
    )


# replace spaces with underscores, and remove blacklisted characters
# only use the first 150 characters to avoid filenames that are too long
# name = "hello world!"
def get_valid_filename(name):
    return re.sub(r"(?u)[^-\w.]", "", name.strip().replace(" ", "_"))[0:150]


# get unique urls and create an id
# search_results_data = parse_search_pages(search_pages_folder)
def get_product_url_data(search_results_data):
    unique_urls = list(set(search_results_data.loc[:, "url"]))
    return DataFrame(
        {
            "url": unique_urls,
            "product_id": [get_valid_filename(url) for url in unique_urls],
        }
    )
