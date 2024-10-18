import time
import json
from typing import List

import requests
from seleniumwire import webdriver
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup

CATALOG_SLUG: str = ""
ITEMS_COUNT: int = 0
HOST = "https://www.auchan.ru"
HOST_HEADERS = {
    "Cookie": "",
}
API_URL = "https://api.retailrocket.ru/api/1.0/partner/5ecce55697a525075c900196/items/?itemsIds=%(item_id)d&stock=1&format=json"
# Need to add "path" header when you make request because it needs to have itemId in value


def interceptor(request):
    for header, value in HOST_HEADERS.items():
        request.headers[header] = value


def fillInputConstants():
    global CATALOG_SLUG, ITEMS_COUNT
    CATALOG_SLUG = input("Введите slug нужного каталога: ")
    ITEMS_COUNT = int(input("Введите количество товаров, которое необходимо получить: "))


def closePopup(driver):
    try:
        popup = driver.find_element(By.CLASS_NAME, "popup__overlay--after-open")
        if popup:
            button = popup.find_element(By.CLASS_NAME, "css-1a99inm")
            if button:
                button.click()
    except Exception:
        pass


def openPage(driver, url):
    driver.get(url)
    time.sleep(3)
    if driver.title == "HTTP 403":
        raise Exception("Try to change cookie header in `HOST_HEADERS` constant. You need to take it from real website.")
    closePopup(driver)


def openBrowser():
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    driver = webdriver.Chrome(
        options=options
    )
    driver.request_interceptor = interceptor
    openPage(driver, f"{HOST}/catalog/{CATALOG_SLUG}/")
    return driver


def parseItems(driver, acc: List, items_iter: int) -> int:
    soup = BeautifulSoup(driver.page_source, 'lxml')
    all_items = soup.find_all("div", attrs={"data-offer-id": True})
    for item in all_items:
        if ITEMS_COUNT <= items_iter:
            break
        item_id = int(item.attrs["data-offer-id"])
        item_url = API_URL % {"item_id": item_id}
        response = requests.get(item_url)
        data = json.loads(response.content)[0]
        new_item = {
            "id": data["ItemId"],
            "name": data["Name"],
            "link": data["Url"],
            "regular_price": data["Price"] if not data["OldPrice"] else data[
                "OldPrice"],
            "promo_price": None if not data["OldPrice"] else data["Price"],
            "brand": data["Vendor"],
        }
        acc.append(new_item)
        items_iter += 1
        time.sleep(.3)
    return items_iter


def main():
    fillInputConstants()
    browser = openBrowser()
    result = list()
    items_count = parseItems(browser, result, 0)
    while items_count < ITEMS_COUNT:
        try:
            pagination_arrow_right = browser.find_element(By.CLASS_NAME, "pagination-arrow--right")
            if pagination_arrow_right:
                link = pagination_arrow_right.find_element(By.TAG_NAME, "a").get_attribute("href")
                openPage(browser, link)
            items_count += parseItems(browser, result, items_count)
        except Exception as e:
            break

    with open("result.json", "a") as file:
        file.write(json.dumps(result))

    print("Товары были успешно добалены в файл!" if len(result) else "Товары не были найдены!")


if __name__ == "__main__":
    main()
