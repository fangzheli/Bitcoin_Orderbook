#######################################
# this is the main script to maintain a live order book which retrieves bitcoin
# transaction data from Coinbase websocket feed full channel
# Author: Fangzhe Li
# Date : Sep-22-2022
#
import websocket
import json
from sortedcontainers import SortedDict
from websocket import WebSocketConnectionClosedException
import decimal
import requests
import time
from customFormatter import CustomFormatter
import logging

# set a global logger for debugging/demo purpose,
logger = logging.getLogger(__name__)
# you can change logging level from logging.INFO to logging.DEBUG
# in order to show all message received from Coinbase websocket server
logger.setLevel(logging.INFO)  # show all message whose level >= INFO
logHandler = logging.StreamHandler()
# set log message format
fmt = '%(threadName)s|%(asctime)s|%(levelname)s|%(message)s'
# use CustomFormatter to show different level log message with different color
logHandler.setFormatter(CustomFormatter(fmt))
logger.addHandler(logHandler)


class WebsocketClient:
    def __init__(self, product_ids=["BTC-USD"], channels=["full"], url='wss://ws-feed.exchange.coinbase.com'):
        #
        self.url = url
        self.product_ids = product_ids
        self.channels = channels
        self.ws = None
        self.stop_flag = True

    def get_product_ids(self):
        return self.product_ids

    def on_open(self):
        logger.info("Opened {} connection: product_ids = {}"
                    .format(self.channels, self.product_ids))

    def on_close(self):
        logger.info("### closed ###")

    def on_message(self, message):
        logger.debug(json.dumps(message, indent=4, sort_keys=True))

    def on_error(self, error):
        logger.error(error)

    def subscribe(self):
        # connect to the websocket
        self.stop_flag = False
        try:
            self.ws = websocket.create_connection(self.url)
        except ConnectionResetError:
            logger.error("got ConnectionResetError when connecting to {}".format(self.url))
            exit(-1)

        params = {
            "type": "subscribe",
            "product_ids": self.product_ids,
            "channels": self.channels
        }
        self.ws.send(json.dumps(params))
        logger.info("in subscribe(),self.ws.connected ={}".format(self.ws.connected))
        self.on_open()
        data = self.ws.recv()
        message = json.loads(data)
        return message

    def listen(self):
        # keep receive message from websocket
        while not self.stop_flag:
            data = self.ws.recv()
            try:
                message = json.loads(data)
            except json.decoder.JSONDecodeError:
                logger.warning('one incomplete message, ignored')
                pass
            # logger.debug("in listen: enter sleep")
            # time.sleep(0.1)
            # logger.debug("in listen: end sleep")
            self.on_message(message)

    def close(self):
        self.stop_flag = True
        try:
            if self.ws:
                self.ws.close()
        except WebSocketConnectionClosedException as e:
            pass
        logger.info("ws client initiates to close the session")
        self.on_close()


class OrderBook(WebsocketClient):
    def __init__(self, product_ids=["BTC-USD"], channels=["full"], url='wss://ws-feed.exchange.coinbase.com'):
        super(OrderBook, self).__init__(product_ids, channels, url)
        self._sequence_id = 0
        self._order_book = {}

        self._orders = dict(buy=None, sell=None)
        self._orders['buy'] = SortedDict()
        self._orders['sell'] = SortedDict()

    def on_open(self):
        logger.info("Welcome to the OrderBook! please Ctrl+C to stop running")
        self.reset_OrderBook()

    def on_close(self):
        logger.info("The OrderBook is closed")

    def on_message(self, message):
        # at first, call parent class' on_message method to
        # show the message for debugging purpose
        super().on_message(message)

        if message.get('type') == "subscriptions":
            logger.debug('subscription response received')
            return
        if message.get('sequence') is None:
            logger.debug("sequence is missing in the message,ignore it")
            return
        message_sequence = message['sequence']
        logger.debug('sequence_id:{}'.format(message_sequence))
        if message_sequence <= self._sequence_id:
            # this is an out-of-date message, just ignore it
            logger.debug('out-of-date message')
            return
        # some messages got missed or this is the first message after subscription
        if message_sequence > self._sequence_id + 1:
            self._sequence_id = message_sequence
            self.reset_OrderBook()
            return
        self._sequence_id = message_sequence
        # handle different message types to update orders status
        message_type = message['type']
        if message_type == "open":
            self.open(message)
        elif message_type == "done":
            self.done(message)
        elif message_type == "match":
            self.match(message)
        elif message_type == "change":
            self.change(message)
        else:
            logger.debug("unknown message type:[{}], ignore it".format(message_type))
            return
        self.show_order_books()

    def open(self, message):
        logger.debug("in open handler")
        order_id = message['order_id']
        side = message["side"]
        price = decimal.Decimal(message['price'])
        size = decimal.Decimal(message['remaining_size'])
        # time = message['time']
        order = {
            "order_id": order_id,
            "size": size
            # 'time': time
        }
        # side is either "buy" or "sell"
        # update self._order_book
        existing_orders = self.get_orders(side)
        if not existing_orders.get(price):
            existing_orders[price] = [order]
        else:
            existing_orders[price].append(order)
        self.set_orders(side, existing_orders)
        return existing_orders

    def done(self, message):
        logger.debug("in done handler")
        order_id = message['order_id']
        side = message["side"]
        price = None
        # for some case, price is not included in message, probably we need to do search on the whole order book
        try:
            price = decimal.Decimal(message['price'])
        except:
            logger.warning("for some case, price is not included in message, probably we need to do search on the "
                           "whole order book")
        size = decimal.Decimal(message['remaining_size'])
        # time = message['time']
        order = {
            "order_id": order_id,
            "size": size
            # 'time': time
        }

        # side can be either "buy" or "sell"
        existing_orders = self.get_orders(side)
        if not price:
            for temp_price, orders in existing_orders.items():
                for o in orders:
                    if o['order_id'] == order['order_id']:  # found it
                        orders.remove(o)  # remove the order completely
                        break  # because order_id is unique, no need to try more
            if not orders:
                del existing_orders[temp_price]
            self.set_orders(side, existing_orders)
        try:
            orders = existing_orders[price]
            for o in orders:
                if o['order_id'] == order['order_id']:
                    orders.remove(o)
                    break
            if not orders:
                del existing_orders[price]
            self.set_orders(side, existing_orders)
        except KeyError:
            logger.debug("no {} order with this price for now".format(side))

        return existing_orders

    def match(self, message):
        logger.debug("in match handler")
        maker_order_id = message['maker_order_id']
        taker_order_id = message['taker_order_id']
        trade_id = message['trade_id']
        side = message["side"]
        price = decimal.Decimal(message['price'])
        size = decimal.Decimal(message['size'])
        time = message['time']
        order = {
            "maker_order_id": maker_order_id,
            "taker_order_id": taker_order_id,
            "size": size,
            'time': time,
        }
        logger.debug("Parameters are parsed properly. Order: %s", extra=order)
        # side can be either "buy" or "sell"
        existing_orders = self.get_orders(side)
        if not existing_orders.get(price):
            return existing_orders
        for o in existing_orders[price]:
            if o['order_id'] == order["maker_order_id"]:
                if o["size"] == order["size"]:
                    existing_orders[price].remove(o)
                if not existing_orders[price]:
                    del existing_orders[price]
                else:
                    o['size'] -= order['size']
                break  # maker_order_id is unique, only one maker_order_id can be matched
        self.set_orders(side, existing_orders)
        return existing_orders

    def change(self, message):
        logger.debug("in change handler")
        old_size = decimal.Decimal(message["old_size"])
        new_size = decimal.Decimal(message["new_size"])
        order_id = message["order_id"]
        side = message["side"]
        time = message['time']

        # side can be either "buy" or "sell"
        existing_orders = self.get_orders(side)
        try:
            reason = message['reason']
        except KeyError:
            logger.warning("get no reason for change message")
            return
        if reason == "STP":
            price = decimal.Decimal(message['price'])
            if not existing_orders.get(price):
                # not initialized or it is a change to received message
                logger.warning("missing a previous price")
                return existing_orders
            else:
                for o in existing_orders[price]:
                    if o['order_id'] == order_id:
                        assert o['size'] == old_size, f"the size {o['size']} to change is not same as " \
                            f"old_size according to the server side {old_size}"
                        o['size'] = new_size
                        self.set_orders(side, existing_orders)
                        return existing_orders
        elif reason == "modify_order":
            old_price = decimal.Decimal(message['old_price'])
            new_price = decimal.Decimal(message['new_price'])
            if not existing_orders.get(old_price):
                # not initialized or it is a change to received message
                logger.warning("missing an old_price")
                return existing_orders
            else:
                for o in existing_orders[old_price]:
                    if o['order_id'] == order_id:
                        # switch to new size
                        assert o['size'] == old_size, f"the size {o['size']} to change is not same as " \
                            f"old_size according to the server side {old_size}"
                        o['size'] = new_size
                        # switch to new price
                        if existing_orders.get(new_price):
                            existing_orders[new_price].append(o)
                        else:
                            existing_orders[new_price] = [o]
                        existing_orders[old_price].remove(o)
                        if not existing_orders[old_price]:
                            del existing_orders[old_price]
                        self.set_orders(side, existing_orders)
                        return existing_orders
        else:
            logger.warning("get other reason for change message")
            return existing_orders

    def reset_OrderBook(self):
        logger.info("resetOrderBook")

        self._orders.clear()
        self._orders['buy'] = SortedDict()
        self._orders['sell'] = SortedDict()

        initial_book = self.get_initial_OrderBook()
        # logger.info(initial_book)
        if initial_book:
            logger.info("resetOrderBook: sequence={}".format(initial_book['sequence']))
            self._sequence_id = initial_book['sequence']
            for side in ('bids', 'asks'):
                book_of_one_side = initial_book[side]
                for o in book_of_one_side:
                    message = {
                        'price': decimal.Decimal(o[0]),
                        'remaining_size': decimal.Decimal(o[1]),
                        'order_id': o[2],
                        'side': 'buy' if side == 'bids' else 'sell'
                    }
                    self.open(message)

            logger.info("Order book initializes successfully")
        else:
            logger.error("resetOrderBook failed")

    def get_initial_OrderBook(self):
        # coinbase doc for product order books to initialize the status
        # https://docs.cloud.coinbase.com/exchange/reference/exchangerestapi_getproductbook-1
        '''
        Return example for level 1, can check out example for level 3 by
        https://api.exchange.coinbase.com/products/BTC-USD/book?level=3
        {
            "sequence": 13051505638,
            "bids": [
                [
                    "6247.58",
                    "6.3578146",
                    2
                ]
            ],
            "asks": [
                [
                    "6251.52",
                    "2",
                    1
                ]
            ]
        }
        '''
        logger.info("Getting initial OrderBook")
        url = 'https://api.exchange.coinbase.com/'
        endpoint = 'products/' + self.product_ids[0] + '/book'
        url = url + endpoint
        # we need level 3 book to initialize our order book
        params = {'level': 3}
        response = requests.Session().get(url, params=params, auth=None, timeout=30)
        return response.json()

    def get_orders(self, side):
        """
        retrieve current orders from either 'buy' or 'sell' side
        :param side:  (String) : either 'buy' or 'sell'
        :return: a SortedDict() whose keys are prices, value is a list which
                include all orders at this price from one side(either buy or sell)
        """
        assert (side in ('buy', 'sell'))
        return self._orders[side]

    def set_orders(self, side, new_orders):
        assert (side in ('buy', 'sell'))
        # logger.debug('set_orders:' + str(new_orders))
        self._orders[side] = new_orders
        return self._orders[side]

    def show_order_books(self, count=5):
        self.update_order_books(count)
        logger.debug(self._order_book)
        for side in ('asks', 'bids'):
            if side == 'asks':
                for item in self._order_book[side][::-1]:
                    logger.info(item[1] + ' @ ' + item[0])
            else:
                for item in self._order_book[side]:
                    logger.info(item[1] + ' @ ' + item[0])
            if side == 'asks':
                logger.info('---------------------')
            else:
                logger.info('=====================')


    def update_order_books(self, count=5):
        """
        construct order book of the best count bids and asks
        self._order_book is updated
        :param count:  how many best prices/quantity items to display
        :return: a dict of most updated order_book
        in the format of
        self._order_book=
            {
            'asks': [
                ['1.02', '200'],
                ['1.01', '300'],
            ],
            'bids': [
                ['0.99', '5'],
                ['0.98', '3'],
            ],

        """
        self._order_book['asks'] = []
        self._order_book['bids'] = []

        for side in ('sell', 'buy'):
            for i in range(count):
                # get i best(smallest) sell prices, or i best(largest) buy prices
                if side == 'sell':
                    temp_price, orders = self.get_orders(side).peekitem(index=i)
                else:
                    temp_price, orders = self.get_orders(side).peekitem(index=-1 * (i + 1))

                item = [str(temp_price), decimal.Decimal(0.00000)]
                # accumulates quantity of the same price order size to a summary
                for o in orders:
                    item[1] += o.get('size')
                item[1] = str(item[1])
                if side == 'sell':
                    self._order_book['asks'].append(item)  # larger prices put in the front
                else:
                    self._order_book['bids'].append(item)  # larger prices put in the back
        # use the assert to find the lock/cross case
        assert self._order_book['asks'][0] > self._order_book['bids'][-1]
        return self._order_book