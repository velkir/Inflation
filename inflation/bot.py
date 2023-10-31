from telegram.ext import Updater, CommandHandler
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from .models import UniqueProduct, ProductPrice, Script
import time
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

chrome_options = Options()
chrome_options.add_argument("--headless")


def add_product(update, context):
    try:
        args = context.args
        product_name, brand, url, js_script, store, country, currency = args

        product = UniqueProduct.objects.create(
            product_name=product_name,
            Brand=brand,
            URL=url,
            Store=store,
            Country=country,
            Currency=currency
        )

        Script.objects.create(
            product=product,
            js_script=f"return {js_script}.innerText"
        )

        update.message.reply_text(f"Added product {product_name}")

    except Exception as e:
        update.message.reply_text(f"Error: {e}")


def fetch_prices(update, context):
    logger.info("Starting fetch_prices function")

    with webdriver.Chrome(options=chrome_options) as driver:
        # products = UniqueProduct.objects.select_related('script').all()
        products = UniqueProduct.objects.prefetch_related('script_set').all()

        if not products:
            logger.warning("No products found in the database")
            return

        for product in products:
            logger.info(f"Fetching price for product: {product.product_name} from URL: {product.URL}")

            max_wait_time = 60  # Максимальное время ожидания в секундах
            wait_time = 4  # Начальное время ожидания в секундах

            driver.get(product.URL)

            while max_wait_time > 0:
                try:
                    # script = product.script.js_script
                    script_obj = product.script_set.first()
                    if script_obj:
                        script = script_obj.js_script

                    price_element = driver.execute_script(script)

                    cleaned_price = ''.join(filter(lambda x: x.isdigit() or x in '.,', price_element))
                    price_value = float(cleaned_price.replace(',', '.'))

                    ProductPrice.objects.create(
                        product=product,
                        price=price_value
                    )

                    update.message.reply_text(f"Fetched price {price_value} for product {product.product_name}")
                    logger.info(f"Successfully fetched price {price_value} for product {product.product_name}")
                    break  # Выход из цикла, если данные успешно получены

                except Exception as e:
                    update.message.reply_text(f"Error fetching price for {product.product_name}. Most likely due to unfinished page loading. \nTrying again.")
                    logger.error(f"Error fetching price for {product.product_name}: {e}")

                    time.sleep(wait_time)  # Ожидание перед повторной попыткой
                    max_wait_time -= wait_time
                    wait_time *= 2  # Удваивание времени ожидания

                    if wait_time > max_wait_time:
                        wait_time = max_wait_time

def echo(update, context):
    update.message.reply_text(update.message.text)

def start_bot():
    updater = Updater(token='6820356537:AAG1b1WZhddI31u4siq63ltzAqRqFuB3Vls', use_context=True)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(CommandHandler("add_product", add_product))
    dispatcher.add_handler(CommandHandler("fetch_prices", fetch_prices))
    dispatcher.add_handler(CommandHandler("echo", echo))
    updater.start_polling()
