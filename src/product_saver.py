from concurrent.futures import ThreadPoolExecutor
import gc
from numpy import array_split, copy
from os import cpu_count, path
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.expected_conditions import (
    presence_of_element_located as located,
)
from selenium.webdriver.support.wait import WebDriverWait as wait
from src.utilities import (
    FoiledAgainError,
    GoneError,
    get_filenames,
    new_browser,
    only,
    save_browser,
    switch_user_agent,
    wait_for_amazon,
    WAIT_TIME,
)
from time import sleep
from urllib3.exceptions import ProtocolError

# product_url = product_url_data.loc[:, "product_url"][0]
def save_product_page(
    thread_id,
    browser,
    ASIN,
    product_pages_folder,
    first_time = False
):
    print("thread {0:d} saving product {1}!".format(thread_id, ASIN))
    browser.get("https://www.amazon.com/dp/" + ASIN)

    wait_for_amazon(browser)
    if first_time:
        try:
            wait(browser, WAIT_TIME).until(
                located((By.CSS_SELECTOR, "button#fs-opt-in"))
            )
            only(browser.find_elements(By.CSS_SELECTOR, "button#fs-opt-in")).click()
        except TimeoutException as an_error:
            pass

    try:
        # wait for fakespot grade
        wait(browser, WAIT_TIME).until(
            located((By.CSS_SELECTOR, "div.fakespot-main-grade-box-wrapper"))
        )
    except TimeoutException:
        # might not be a fakespot grade
        pass

    save_browser(
        browser,
        path.join(product_pages_folder, ASIN + ".html"),
    )
    gc.collect()

def save_product_pages(
    thread_id,
    product_ASINs,
    product_pages_folder,
    user_agents,
    user_agent_index=0,
):
    print("started thread {0:d}!".format(thread_id))
    browser = new_browser(user_agents[user_agent_index], fakespot=True)

    completed_product_filenames = get_filenames(product_pages_folder)
    first_time = True

    # no previous product, so starts empty
    # product_url = product_url_data.loc[:, "url"][0]
    for ASIN in product_ASINs:
        # don't save a product we already have
        if ASIN in completed_product_filenames:
            continue

        try:
            save_product_page(
                thread_id,
                browser,
                ASIN,
                product_pages_folder,
                first_time
            )
        except GoneError:
            # if the product is gone, print some debug information, and just continue
            print(str(ASIN))
            print("Page no longer exists, skipping")
            continue
        except TimeoutException:
            # if the product times out, print some debug information, and just continue
            # come back to get it later
            print(str(ASIN))
            print("Timeout, skipping")
            continue
        except ProtocolError:
            print("WiFi dropped, sleeping and retrying")
            sleep(60)
            try:
                save_product_page(
                    thread_id,
                    browser,
                    ASIN,
                    product_pages_folder,
                    first_time
                )
            # hande the errors above again, except for the FoiledAgain error
            # if there's still a captcha this time, just give up
            except GoneError:
                print(str(ASIN))
                print("Page no longer exists, skipping")
                continue
            except TimeoutException:
                print(str(ASIN))
                print("Timeout, skipping")
                continue
            except FoiledAgainError:
                browser, user_agent_index = switch_user_agent(
                    browser, user_agents, user_agent_index
                )
                try:
                    save_product_page(
                        thread_id,
                        browser,
                        ASIN,
                        product_pages_folder,
                        first_time
                    )
                # hande the errors above again, except for the FoiledAgain error
                # if there's still a captcha this time, just give up
                except GoneError:
                    print(str(ASIN))
                    print("Page no longer exists, skipping")
                    continue
                except TimeoutException:
                    print(str(ASIN))
                    print("Timeout, skipping")
                    continue
        except FoiledAgainError:
            browser, user_agent_index = switch_user_agent(
                browser, user_agents, user_agent_index
            )
            try:
                save_product_page(
                    thread_id,
                    browser,
                    ASIN,
                    product_pages_folder,
                    first_time
                )
            # hande the errors above again, except for the FoiledAgain error
            # if there's still a captcha this time, just give up
            except GoneError:
                print(str(ASIN))
                print("Page no longer exists, skipping")
                continue
            except TimeoutException:
                print(str(ASIN))
                print("Timeout, skipping")
                continue
            except ProtocolError:
                print("WiFi dropped, sleeping and retrying")
                sleep(60)
                try:
                    save_product_page(
                        thread_id,
                        browser,
                        ASIN,
                        product_pages_folder,
                        first_time,
                    )
                # hande the errors above again, except for the FoiledAgain error
                # if there's still a captcha this time, just give up
                except GoneError:
                    print(str(ASIN))
                    print("Page no longer exists, skipping")
                    continue
                except TimeoutException:
                    print(str(ASIN))
                    print("Timeout, skipping")
                    continue
        first_time = False

    browser.close()
    print("finished thread {0:d}!".format(thread_id))

    return user_agent_index

def multithread_save_product_pages(threads, user_agents, ASINs, product_pages_folder):
    with ThreadPoolExecutor() as executor:
        for result in executor.map(
            lambda thread_id, sub_product_list, sub_user_agent_list: save_product_pages(
                thread_id,
                copy(sub_product_list),
                product_pages_folder,
                copy(sub_user_agent_list),
            ),
            range(threads),
            array_split(
                ASINs, threads
            ),
            array_split(user_agents, threads),
        ):
            print(result)
