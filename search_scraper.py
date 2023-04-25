from bs4 import BeautifulSoup
from os import chdir, path
from pandas import concat

FOLDER = "/home/brandon/amazon_scraper"
chdir(FOLDER)
from utilities import dicts_to_dataframe, get_filenames, only

def parse_search_result(query, search_result, index):
    product_data = {"search_term": query, "rank": index + 1}

    # sponsored_tags = search_result.select(
    #     ".puis-label-popover-default"
    # )
    # if len(sponsored_tags) > 0:
    #     # sanity check
    #     only(sponsored_tags)
    #     product_data["ad"] = True

    product_data["url"] = only(
        search_result.select(
            # a link in a heading
            "h2 a",
        )
    )["href"]

    # limited_time_deal_label = search_result.select(
    #     "span[data-a-badge-color='sx-lighting-deal-red']"
    # )
    
    # if limited_time_deal_label is not None:
    #     only(limited_time_deal_label)
    #     product_data["limited_time_deal"] = True

    # provenance_certifications = search_result.select(
    #     By.XPATH, "//*[contains(@data-s-pc-popover, 'provenanceCertifications')]"
    # )
    # if len(provenance_certifications) > 0:
    #     product_data["provenance_certifications"] = provenance_certifications.text 

    # images = search_result.select(
    #     "img[class='s-image']"
    # )
    # for image in images:
    #     if image.get_attribute("src") == "https://m.media-amazon.com/images/I/111mHoVK0kL._SS200_.png":
    #         product_data["small_business"] = True

    return product_data

# index = 0
# search_result = BeautifulSoup(open(path.join(search_pages_folder, query + ".html"), 'r'), 'lxml').select("div.s-main-slot.s-result-list > div[data-component-type='s-search-result']")[0]
def parse_search_results(search_pages_folder, query):
    file = open(path.join(search_pages_folder, query + ".html"), 'r')
    result = dicts_to_dataframe(
        parse_search_result(query, search_result, index)
        for index, search_result in enumerate(BeautifulSoup(file, 'lxml').select(
            "div.s-main-slot.s-result-list > div[data-component-type='s-search-result']",
        ))
    )
    file.close()
    return result

# query = "dog food"
def scrape_searches(search_pages_folder):
    return concat(
        parse_search_results(search_pages_folder, query)
        for query in get_filenames(search_pages_folder)
    )
