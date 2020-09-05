# Standard Library
from datetime import datetime
import json
import logging
import os

# Third Party Library
import requests
from bs4 import BeautifulSoup
import boto3

logger = logging.getLogger()
logger.setLevel(getattr(logging, os.environ["logLevel"], 40))


def notify(email, api_key, message):
    push_end_point = "https://api.pushbullet.com/v2/pushes"
    key = get_secret_parameter(api_key)
    body = str(message).strip("[]")
    payload = {
        "body": body,
        "title": "Waste Collection Details",
        "type": "note",
        "email": email,
    }
    resp = requests.post(
        push_end_point,
        headers={"Access-Token": key, "Content-Type": "application/json"},
        data=json.dumps(payload),
    )
    logger.info(resp.json())


def lambda_handler(event, context):

api_key = os.environ["apiKey"]
    email = os.environ["email"]
    council_web_page = (
        "https://digital.wyndham.vic.gov.au"
        + "/myWyndham/init-map-data.asp?"
        + "propnum=172369&radius=2000"
    )
    page = requests.get(council_web_page)

    soup = BeautifulSoup(page.content, "html.parser")

    collection_information = soup.find_all("div", class_="infocaritem")
    bin_dates = {}
    for item in collection_information[4:7]:
        logger.info(item.text)
        temp = item.text.split(":")
        if "Garbage" in temp[0]:
            bin_dates["Garbage"] = get_date(temp[1])
        if "Green" in temp[0]:
            bin_dates["Green"] = get_date(temp[1])
        if "Recycling" in temp[0]:
            bin_dates["Recycling"] = get_date(temp[1])

    bins = get_this_week_bins(bin_dates)
    notify(email, api_key, bins)

    return


def get_secret_parameter(parameter_name):
    """Function to retrieve the secret from Parameter Store
    Parameters:
        parameter_name: String, Required.
    Returns:
        Value:returns the secret
    """
    logger.info(f"Begin get_secret_parameter with {parameter_name=}")
    ssmClient = boto3.client("ssm")
    resp = ssmClient.get_parameter(Name=parameter_name, WithDecryption=True)
    param_value = resp["Parameter"]["Value"]
    logger.info("retrieval of secret password")
    return param_value


def get_date(day_date):
    date_string = day_date.split(",")[1].strip()
    logger.info(f"get_date {date_string=}")
    date = datetime.strptime(date_string, "%d %B %Y")
    return date.strftime("%d-%m-%Y")


def get_this_week_bins(bins_dict):
    ret_val = []
    now = datetime.now()
    # isocalendar retruns (YYYY, week no in year, dd)
    sysdate_week_no = now.isocalendar()[1]

    bin_collection_date = ""

    for key, val in bins_dict.items():
        bin_date = datetime.strptime(val, "%d-%m-%Y")
        bin_date_week_no = bin_date.isocalendar()[1]
        if sysdate_week_no == bin_date_week_no:
            ret_val.append(key)
            bin_collection_date = val

    ret_val.insert(0, bin_collection_date)
    return ret_val


if __name__ == "__main__":
    lambda_handler("", "")
