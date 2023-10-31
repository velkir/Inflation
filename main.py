import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from sqlalchemy.exc import IntegrityError
from sqlalchemy import (
    create_engine,
    Table,
    Column,
    Integer,
    String,
    Float,
    ForeignKey,
    DateTime,
    func,
    MetaData,
)

DATABASE_URL = "sqlite:///prices.db"
metadata = MetaData()

# Таблица unique_products
unique_products = Table(
    "unique_products",
    metadata,
    Column("product_id", Integer, primary_key=True, autoincrement=True),
    Column("product_name", String, nullable=False),
    Column("Brand", String, nullable=False),
    Column("URL", String, nullable=False, unique=True),
    Column("Store", String, nullable=False),
    Column("Country", String, nullable=False),
    Column("Currency", String, nullable=False),
)


# Таблица product_prices
product_prices = Table(
    "product_prices",
    metadata,
    Column("price_id", Integer, primary_key=True, autoincrement=True),
    Column(
        "product_id", Integer, ForeignKey("unique_products.product_id"), nullable=False
    ),
    Column("price", Float, nullable=False),
    Column("timestamp", DateTime, default=func.now(), nullable=False),
)

# Таблица scripts
scripts = Table(
    "scripts",
    metadata,
    Column("script_id", Integer, primary_key=True, autoincrement=True),
    Column(
        "product_id", Integer, ForeignKey("unique_products.product_id"), nullable=False
    ),
    Column("js_script", String, nullable=False),
)

engine = create_engine(DATABASE_URL)
metadata.create_all(engine)

chrome_options = Options()
chrome_options.add_argument("--headless")


def add_product(product_name, product_url, brand, js_script, store, country, currency):
    with engine.connect() as conn:
        try:
            product_result = conn.execute(
                unique_products.insert().values(
                    product_name=product_name,
                    URL=product_url,
                    Brand=brand,
                    Store=store,
                    Country=country,
                    Currency=currency,
                )
            )
            product_id = product_result.inserted_primary_key[0]
            conn.execute(
                scripts.insert().values(
                    product_id=product_id, js_script=f"return {js_script}.innerText"
                )
            )
            conn.commit()
            print(f"Added product '{product_name}' with ID {product_id}")

        except IntegrityError:
            print(
                f"Error: Product with name '{product_name}' or URL '{product_url}' already exists in the database."
            )
            conn.rollback()


def fetch_prices():
    with engine.connect() as conn:
        products_and_scripts = conn.execute(
            unique_products.join(scripts).select()
        ).fetchall()

        with webdriver.Chrome(options=chrome_options) as driver:
            for product in products_and_scripts:
                driver.get(product.URL)

                max_wait_time = 15  # Максимальное время ожидания в секундах
                wait_time = 3  # Начальное время ожидания в секундах

                while max_wait_time > 0:
                    try:
                        script = product.js_script
                        price_element = driver.execute_script(script)

                        cleaned_price = "".join(
                            filter(lambda x: x.isdigit() or x in ".,", price_element)
                        )
                        price_value = float(cleaned_price.replace(",", "."))

                        conn.execute(
                            product_prices.insert().values(
                                product_id=product.product_id, price=price_value
                            )
                        )
                        conn.commit()

                        print(
                            f"Fetched price {price_value} for product {product.product_name}"
                        )
                        break  # Выход из цикла, если данные успешно получены

                    except Exception as e:
                        print(f"Error fetching price for {product.product_name}: {e}")
                        time.sleep(wait_time)  # Ожидание перед повторной попыткой
                        max_wait_time -= wait_time
                        wait_time *= 2  # Удваивание времени ожидания

                        if wait_time > max_wait_time:
                            wait_time = max_wait_time


def main():
    # Пример добавления продукта
    add_product(
        product_name="Apple",
        product_url="https://zakupy.auchan.pl/shop/auchan-jablka.p-149427",
        brand="Auchan",
        js_script='document.querySelector("#productDetails > div > div._2Qj8._3yML._1heG.p-Jk._3drr._3C3T.hqot._130n._1Aqm > div > div.AqIs")',
        store="Auchan",
        country="Poland",
        currency="PLN",
    )


    add_product(
        product_name="Nutella",
        product_url="https://zakupy.auchan.pl/shop/nutella-krem-do-smarowania-z-orzechami-laskowymi-i-kakao.p-517659",
        brand="Ferrero",
        js_script='document.querySelector("#productDetails > div > div._2Qj8._3yML._1heG.p-Jk._3drr._3C3T.hqot._130n._1Aqm > div > div.AqIs")',
        store="Auchan",
        country="Poland",
        currency="PLN",
    )

    # add_product(
    #     product_name="Nutella",
    #     product_url="https://www.tesco.com/groceries/en-GB/products/263914432",
    #     brand="Heinz",
    #     js_script='document.querySelector("#asparagus-root > div > div.template-wrapper > main > div > div > div.styled__PDPTileContainer-mfe-pdp__sc-ebmhjv-0.cEAseF.pdp-tile > div > section.styled__GridSection-mfe-pdp__sc-ebmhjv-1.bjEIyj > div.styled__Details-mfe-pdp__sc-ebmhjv-7.dqYwFc > div.styled__BuyBoxContainer-mfe-pdp__sc-ebmhjv-5.hkkbie > div > div > div.base-components__RootElement-sc-150pv2j-1.styled__Container-sc-v0qv7n-0.hjMZDF.gVxPxM.styled__StyledPrice-sc-159tobh-5.grMosf.ddsweb-buybox__price.ddsweb-price__container > p.styled__StyledHeading-sc-1a9r96t-2.gSatyL.styled__Text-sc-v0qv7n-1.ecTMDe")',
    #     store="Tesco",
    #     country="UK",
    #     currency="GBP",
    # )

    # add_product(
    #     product_name="Ketchup",
    #     product_url="https://www.walmart.com/ip/Heinz-Tomato-Ketchup-20-oz-Bottle/15077427?athbdg=L1600&from=/search",
    #     brand="Heinz",
    #     js_script='document.querySelector("#maincontent > section > main > div.flex.undefined.flex-column.h-100 > div:nth-child(2) > div > div.w_aoqv.w_wRee.w_fdPt > div > div:nth-child(2) > div > div > div.nowrap.items-center.inline-flex > span.w_iUH7")',
    #     store="Walmart",
    #     country="USA",
    #     currency="USD",
    # )

    add_product(
        product_name="Milk 3.2%",
        product_url="https://zakupy.auchan.pl/shop/laciate-mleko-swieze-32percent.p-41595",
        brand="Łaciate",
        js_script='document.querySelector("#productDetails > div > div._2Qj8._3yML._1heG.p-Jk._3drr._3C3T.hqot._130n._1Aqm > div > div.AqIs")',
        store="Auchan",
        country="Poland",
        currency="PLN",
    )

    # Извлечение и сохранение цен для всех продуктов
    fetch_prices()


if __name__ == "__main__":
    main()
