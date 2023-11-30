from src.funcs import setup, multithread_save_product_pages

(queries, search_results_folder, product_pages_folder) = setup()

multithread_save_product_pages(
    queries,
    search_results_folder,
    product_pages_folder
)
