#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
import threading
from Orderbook.services import logger
from Orderbook.services import OrderBook


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Coinbase_Pro_Orderbook.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


# global BTC_OrderBook
import config
config.BTC_OrderBook = OrderBook(["BTC-USD"], ["full"])


def background_task():
    # coinbase_url = 'wss://ws-feed.exchange.coinbase.com'
    response = config.BTC_OrderBook.subscribe()
    logger.info(response)
    try:
        config.BTC_OrderBook.listen()
        logger.info(response)
    except KeyboardInterrupt:
        config.BTC_OrderBook.close()


# start daemon serve thread that does actual heavy-lifting to construct order_book
serve_thread = threading.Thread(name='coinbase_data_collector Thread', target=background_task)
serve_thread.setDaemon(True)
serve_thread.start()
logger.info(serve_thread.getName() + " has started")


django_thread = threading.Thread(name='Django Thread', target=main)
django_thread.setDaemon(True)
django_thread.start()
logger.info(django_thread.getName() + " has started")


if __name__ == '__main__':
    main()
