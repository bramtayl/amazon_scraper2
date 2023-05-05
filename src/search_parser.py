
from pandas import concat, DataFrame
from src.utilities import get_filenames, get_valid_filename, only, read_html

# index = 0
# file = open(path.join(search_pages_folder, search_id + ".html"), "r")
# search_result = read_html(search_pages_folder, search_id).select("div.s-main-slot.s-result-list > div[data-component-type='s-search-result']")[index]
# file.close()
def parse_search_result(search_id, search_result, index):
    sponsored = False
    sponsored_tags = search_result.select(
        "a[aria-label='View Sponsored information or leave ad feedback']"
    )
    if len(sponsored_tags) > 0:
        # sanity check
        only(sponsored_tags)
        sponsored = True
    
    product_url = only(
        search_result.select(
            # a link in a heading
            "h2 a",
        )
    )["href"]

    return DataFrame(
        {
            "search_id": search_id,
            "rank": index + 1,
            "product_url": product_url,
            "sponsored": sponsored,
            "product_filename": get_valid_filename(product_url)
        },
        # one row
        index=range(1),
    )

class DuplicateProductFilenames(Exception):
    pass

def parse_search_page(search_pages_folder, search_id):
    search_results = concat(
        (
            parse_search_result(search_id, search_result, index)
            for index, search_result in enumerate(
                read_html(search_pages_folder, search_id).select(", ".join([
                    "div.s-main-slot.s-result-list > div[data-component-type='s-search-result']",
                    "div.s-main-slot.s-result-list > div[cel_widget_id*='MAIN-VIDEO_SINGLE_PRODUCT']"
                ]))
            )
        ),
        ignore_index=True
    )
    if len(set(search_results.loc[:, "product_url"])) != len(set(search_results.loc[:, "product_filename"])):
        raise DuplicateProductFilenames()
    
    return search_results


def parse_search_pages(search_pages_folder):
    return concat(
        (
            parse_search_page(search_pages_folder, search_id)
            for search_id in get_filenames(search_pages_folder)
        ),
        ignore_index=True,
    )

# TODO: why did painkillers get cut off?