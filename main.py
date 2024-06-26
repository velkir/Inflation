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
    # Извлечение и сохранение цен для всех продуктов



    # fetch_prices()


if __name__ == "__main__":
    main()
