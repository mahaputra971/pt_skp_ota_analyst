from logging import Logger
from typing import List, Optional

import typer
from core.scrape import Scrape
from typing_extensions import Annotated

# Inisialisasi aplikasi Typer
app = typer.Typer()


@app.command()
def execute(
    hotel_name: Annotated[
        str, typer.Argument(default=..., help="Hotel name from booking.com url")
    ],
    country: Annotated[
        str,
        typer.Argument(
            default=...,
            help="Two character country code (ALPHA-2 code) e.g. 'us'. Visit this link: https://www.iban.com/country-codes",
        ),
    ],
    sort_by: Annotated[
        str,
        typer.Option(
            help="Sort reviews by 'most_relevant', 'newest_first', 'oldest_first', 'highest_scores' or 'lowest_scores'",
            rich_help_panel="Secondary Arguments",
        ),
    ] = "most_relevant",
    n_reviews: Annotated[
        int,
        typer.Option(
            help="Number of reviews to scrape from the top. -1 means scrape all. The reviews will be scraped according to the 'sort_by' option",
            rich_help_panel="Secondary Arguments",
        ),
    ] = -1,
    stop_criteria_username: Annotated[
        Optional[str],  # FIX: Gunakan Optional karena default-nya None
        typer.Option(
            help="username of the review. Stop further scraping when review of this username is found",
            rich_help_panel="Secondary Arguments",
        ),
    ] = None,
    stop_criteria_review_title: Annotated[
        Optional[str],  # FIX: Gunakan Optional karena default-nya None
        typer.Option(
            help="Review title to find. Stop further scraping when given username and review title is found",
            rich_help_panel="Secondary Arguments",
        ),
    ] = None,
    save_review_to_disk: Annotated[
        bool,
        typer.Option(
            help="Whether to save reviews on the local disk or not",
            rich_help_panel="Secondary Arguments",
        ),
    ] = True,
):
    input_params = {
        "hotel_name": hotel_name,
        "country": country,
        "sort_by": sort_by,
        "n_rows": n_reviews,
    }

    # Logika Stop Criteria
    if stop_criteria_username:
        stop = {"username": stop_criteria_username}

        if stop_criteria_review_title:
            stop["review_text_title"] = stop_criteria_review_title

        # FIX: Perbaikan Typo dari 'stop_critera' menjadi 'stop_criteria'
        input_params["stop_criteria"] = stop

    s = Scrape(input_params, save_data_to_disk=save_review_to_disk)
    ls_reviews = s.run()
    print(f"Scrapping Complete: Total Reviews  {len(ls_reviews)}")


def run_as_module(
    hotel_name: str,
    country: str,
    sort_by: str = "newest_first",
    n_reviews: int = -1,
    save_to_disk: bool = True,
    stop_cri_user: str = "",
    stop_cri_title: str = "",
    logger: Optional[Logger] = None, # FIX: Menggunakan Optional agar kompatibel
) -> List[dict]:
    """To run the scrapper as module by third party code"""

    input_params = {
        "hotel_name": hotel_name,
        "country": country,
        "sort_by": sort_by,
        "n_rows": n_reviews,
    }

    if stop_cri_user:
        stop = {"username": stop_cri_user}

        if stop_cri_title:
            stop["review_text_title"] = stop_cri_title

        # FIX: Perbaikan Typo dari 'stop_critera' menjadi 'stop_criteria'
        input_params["stop_criteria"] = stop

    s = Scrape(input_params, save_data_to_disk=save_to_disk, logger=logger)
    ls_reviews = s.run()
    print(f"Scrapping Complete: Total Reviews  {len(ls_reviews)}")
    return ls_reviews


if __name__ == "__main__":
    # FIX: Menggunakan app() agar decorator @app.command() berfungsi dengan benar
    app()