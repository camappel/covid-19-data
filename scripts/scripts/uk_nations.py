from datetime import datetime
import os
import pytz
import requests

import pandas as pd
from uk_covid19 import Cov19API

from cowidev.utils.utils import get_project_dir
from utils.db_imports import import_dataset

DATASET_NAME = "uk_covid_data"
PROJECT_DIR = get_project_dir()
OUTPUT_DIR = os.path.join(PROJECT_DIR, "scripts", "grapher")
OUTPUT_CSV = os.path.join(OUTPUT_DIR, f"{DATASET_NAME}.csv")
ZERO_DAY = "2020-01-01"


def get_uk() -> pd.DataFrame:
    # Absolute
    filters = ["areaType=overview"]
    structure = {
        "Year": "date",
        "Country": "areaName",
        "areaCode": "areaCode",
        "weekly_cases_rolling": "newCasesByPublishDateRollingSum",
        "cumulative_cases": "cumCasesByPublishDate",
        "weekly_deaths_rolling": "newDeaths28DaysByPublishDateRollingSum",
        "cumulative_deaths": "cumDeaths28DaysByPublishDate",
        "daily_deaths": "newDeaths28DaysByPublishDate",
        "daily_cases": "newCasesByPublishDate",
        "test_positivity_rate": "uniqueCasePositivityBySpecimenDateRollingSum",
        "weekly_hospital_admissions": "newAdmissionsRollingSum",
        "people_in_hospital": "hospitalCases",
    }
    api = Cov19API(filters=filters, structure=structure)
    uk = api.get_dataframe()

    # Rate
    filters = ["areaType=overview"]
    structure = {
        "Year": "date",
        "Country": "areaName",
        "areaCode": "areaCode",
        "cumulative_cases_rate": "cumCasesByPublishDateRate",
        "cumulative_deaths_rate": "cumDeaths28DaysByPublishDateRate",
        "weekly_cases_rate": "newCasesByPublishDateRollingRate",
        "weekly_deaths_rate": "newDeaths28DaysByDeathDateRollingRate",
    }
    api = Cov19API(filters=filters, structure=structure)
    uk_rate = api.get_dataframe()

    # Merge
    return pd.merge(uk, uk_rate)


def get_nation() -> pd.DataFrame:
    # Absolute
    filters = ["areaType=nation"]
    structure = {
        "Year": "date",
        "Country": "areaName",
        "areaCode": "areaCode",
        "cumulative_cases": "cumCasesByPublishDate",
        "cumulative_deaths": "cumDeaths28DaysByPublishDate",
        "weekly_cases_rolling": "newCasesByPublishDateRollingSum",
        "weekly_deaths_rolling": "newDeaths28DaysByPublishDateRollingSum",
        "daily_deaths": "newDeaths28DaysByPublishDate",
        "daily_cases": "newCasesByPublishDate",
        "test_positivity_rate": "uniqueCasePositivityBySpecimenDateRollingSum",
        "weekly_hospital_admissions": "newAdmissionsRollingSum",
        "people_in_hospital": "hospitalCases",
    }
    api = Cov19API(filters=filters, structure=structure)
    nation = api.get_dataframe()

    # Rate
    filters = ["areaType=nation"]
    structure = {
        "Year": "date",
        "Country": "areaName",
        "areaCode": "areaCode",
        "cumulative_cases_rate": "cumCasesByPublishDateRate",
        "cumulative_deaths_rate": "cumDeaths28DaysByPublishDateRate",
        "weekly_cases_rate": "newCasesByPublishDateRollingRate",
        "weekly_deaths_rate": "newDeaths28DaysByDeathDateRollingRate",
    }
    api = Cov19API(filters=filters, structure=structure)
    nation_rate = api.get_dataframe()

    # Merge
    return pd.merge(nation, nation_rate)


def get_local() -> pd.DataFrame:
    # Absolute
    filters = ["areaType=utla"]
    metrics = {
        "Year": "date",
        "Country": "areaName",
        "areaCode": "areaCode",
        "cumulative_cases": "cumCasesByPublishDate",
        "cumulative_deaths": "cumDeaths28DaysByPublishDate",
        "weekly_cases_rolling": "newCasesByPublishDateRollingSum",
        "weekly_deaths_rolling": "newDeaths28DaysByPublishDateRollingSum",
        "daily_deaths": "newDeaths28DaysByPublishDate",
        "daily_cases": "newCasesByPublishDate",
        "test_positivity_rate": "uniqueCasePositivityBySpecimenDateRollingSum",
    }
    api = Cov19API(filters=filters, structure=metrics)
    local = api.get_dataframe().sort_values("Year")

    # Rate
    url_local_rate = (
        "https://api.coronavirus.data.gov.uk/v2/data?areaType=utla&metric=cumCasesByPublishDateRate&"
        "metric=cumDeaths28DaysByPublishDateRate&metric=newCasesByPublishDateRollingRate&"
        "metric=newDeaths28DaysByDeathDateRollingRate"
    )
    local_rate = requests.get(url_local_rate).json()
    local_rate = pd.DataFrame.from_records(local_rate["body"], exclude=["areaType"])
    local_rate = local_rate.rename(
        columns={
            "areaName": "Country",
            "date": "Year",
            "cumCasesByPublishDateRate": "cumulative_cases_rate",
            "cumDeaths28DaysByPublishDateRate": "cumulative_deaths_rate",
            "newCasesByPublishDateRollingRate": "weekly_cases_rate",
            "newDeaths28DaysByDeathDateRollingRate": "weekly_deaths_rate",
        }
    )

    # Merge
    return pd.merge(local, local_rate)


def get_nhs_region() -> pd.DataFrame:
    filters = ["areaType=nhsRegion"]
    metrics = {
        "Year": "date",
        "Country": "areaName",
        "areaCode": "areaCode",
        "weekly_hospital_admissions": "newAdmissionsRollingSum",
        "people_in_hospital": "hospitalCases",
    }
    api = Cov19API(filters=filters, structure=metrics)
    return api.get_dataframe()


def get_day_diff(dt):
    return (datetime.strptime(dt, "%Y-%m-%d") - datetime.strptime(ZERO_DAY, "%Y-%m-%d")).days


def generate_dataset():
    combined = pd.concat([get_uk(), get_nation(), get_local(), get_nhs_region()])
    combined = combined.drop_duplicates(subset=["Country", "Year"], keep="first")

    combined["daily_cases_rolling_average"] = combined["weekly_cases_rolling"] / 7
    combined["daily_deaths_rolling_average"] = combined["weekly_deaths_rolling"] / 7
    combined["daily_cases_rate_rolling_average"] = combined["weekly_cases_rate"] / 7
    combined["daily_deaths_rate_rolling_average"] = combined["weekly_deaths_rate"] / 7
    combined["new_hospital_admissions"] = combined["weekly_hospital_admissions"] / 7

    combined["Year"] = combined["Year"].apply(get_day_diff)

    combined = combined[["Country"] + [col for col in combined.columns if col != "Country"]]
    combined = (
        combined.dropna(how="any", subset=["weekly_cases_rolling"])
        .drop(columns="areaCode")
        .sort_values(["Country", "Year"])
    )

    # Export
    combined.to_csv(OUTPUT_CSV, index=False)


def update_db():
    time_str = datetime.now().astimezone(pytz.timezone("Europe/London")).strftime("%-d %B, %H:%M")
    source_name = f"UK Government Coronavirus (COVID-19) Dashboard – Last updated {time_str} (London time)"
    import_dataset(
        dataset_name=DATASET_NAME,
        namespace="owid",
        csv_path=OUTPUT_CSV,
        default_variable_display={"yearIsDay": True, "zeroDay": ZERO_DAY},
        source_name=source_name,
        slack_notifications=True,
    )


if __name__ == "__main__":
    generate_dataset()
