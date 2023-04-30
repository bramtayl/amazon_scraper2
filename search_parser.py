from bs4 import BeautifulSoup
from os import chdir, path
from pandas import concat

FOLDER = "/home/brandon/amazon_scraper"
chdir(FOLDER)
from utilities import dicts_to_dataframe, get_filenames, only


def parse_search_result(query, search_result, index):
    search_result_row = {"search_term": query, "rank": index + 1}

    search_result_row["url"] = only(
        search_result.select(
            # a link in a heading
            "h2 a",
        )
    )["href"]

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

    return search_result_row


# query = "dog food"
def parse_search_page(search_pages_folder, query):
    file = open(path.join(search_pages_folder, query + ".html"), "r")
    # index = 0
    # search_result = BeautifulSoup(file, 'lxml').select("div.s-main-slot.s-search_results_data-list > div[data-component-type='s-search-search_results_data']")[index]
    search_results_data = dicts_to_dataframe(
        parse_search_result(query, search_result, index)
        for index, search_result in enumerate(
            BeautifulSoup(file, "lxml").select(
                "div.s-main-slot.s-result-list > div[data-component-type='s-search-result']",
            )
        )
    )
    file.close()
    return search_results_data


def parse_search_pages(search_pages_folder):
    all_data = concat(
        parse_search_page(search_pages_folder, query)
        for query in get_filenames(search_pages_folder)
    )
    # add some ids for convenience
    # TODO: there might be some repeated products across different searches
    all_data["product_id"] = range(all_data.shape[0])
    return all_data
