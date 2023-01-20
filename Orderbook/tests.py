from django.test import TestCase
import unittest
from Orderbook.services import OrderBook
from sortedcontainers import SortedDict
import decimal
import json


class TestOrderBook(unittest.TestCase):


    def test_get_product_ids(self):
        print("test_get_product_ids")
        ob = OrderBook(["BTC-USD", "ETC-USD"], ["full"])
        self.assertEqual(ob.get_product_ids(), ["BTC-USD", "ETC-USD"])
        print("test_get_product_ids: pass")

    def test_open_order(self):
        """
        initial state: 'buy' orders are empty
        test case:  1. one buy order with 'open' type message received,
                    2. second buy order with 'open' type message received, price is the same
                    as in step 1
                    3. third buy order with 'open' type message received, price is different

        test goal:  verify OrderBook.open() method can handle above scenarios correctly
        :return:
        """
        print("test_open_order")
        ob = OrderBook(["BTC-USD", "ETC-USD"], ["full"])
        existing_orders = ob.get_orders('buy')
        print(existing_orders)
        # a new open order
        message_open1 = {
            "order_id": '111111111',
            "side": "buy",
            "price": 12345.67,
            "remaining_size": 1
        }
        # a same price open order
        message_open2 = {
            "order_id":'2222222',
            "side": "buy",
            "price": 12345.67,
            "remaining_size": 31
        }
        # a different price open order
        message_open3 = {
            "order_id":'33333',
            "side": "buy",
            "price": 22555.6,
            "remaining_size": 40
        }

        # step 1: receive one open order when orders SortedDict() is empty
        one_order = ob.open(message_open1)
        # print(one_order)

        # first open order received, after handling, there is only one order in the list with the price
        self.assertEqual(
            len(one_order.get(decimal.Decimal(message_open1['price']))), 1)

        # first open order received, verify 'order_id' is set correctly
        self.assertEqual(
            one_order.get(decimal.Decimal(message_open1['price']))[0]['order_id'],
            message_open1['order_id'])

        # step 2: same price orders are put into the same key,
        two_orders = ob.open(message_open2)
        # print(two_orders)

        # verify order2 is appended to existing list under the same price key
        self.assertEqual(
            len(two_orders.get(decimal.Decimal(message_open1['price']))), 2)

        # step 3: a different price 'open' order received
        three_orders = ob.open(message_open3)
        # print(three_orders)
        # different price order is put into a separate key
        self.assertEqual(
            len(three_orders.get(decimal.Decimal(message_open3['price']))), 1)
        print("test_open_order: pass")

    def test_done_order(self):
        """
        initial state: current 'sell' orders has 3 resting orders( 2 orders remaining_size are different)
        test case:  1. one sell order with 'done' type message received, remaining_size is 0
                    2. second sell order with 'done' type message received, remaining_size is
                    not 0


        test goal:  verify OrderBook.done() method can handle both scenarios correctly
                    and remove both orders completely
        :return:
        """
        print('test_done_order :')
        ob = OrderBook(["BTC-USD"], ["full"])
        self._initial_order = dict(sell=None, buy=None)
        self._initial_order['sell'] = SortedDict()
        self._initial_order['buy'] = SortedDict()

        print("step 0: initialize sell order dict:")
        self._initial_order['sell'] = SortedDict({
            decimal.Decimal('18600.01'): [
                {'order_id': 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaa',
                 'size': decimal.Decimal('0.0001344')
                },
                {'order_id': 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb',
                 'size': decimal.Decimal('100.00')
                }
            ],
            decimal.Decimal('18600.02'): [
                {'order_id': 'cccccccc-cccc-cccc-cccc-cccccccccc',
                 'size': decimal.Decimal('0.0001344')
                }
            ]
        })

        existing_sell_orders = ob.set_orders('sell', self._initial_order['sell'])
        # print(existing_sell_orders)


        message_done1 = {
            "order_id": 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaa',
            "price": "18600.01",
            "product_id": "BTC-USD",
            "reason": "canceled",
            "remaining_size": "0.00",
            "sequence": 46662478161,
            "side": "sell",
            "time": "2022-09-25T02:41:37.594700Z",
            "type": "done"
        }
        print("step 1: handle first done message:{}".format(
            json.dumps(message_done1, indent=4, sort_keys=True)))

        new_sell_orders = ob.done(message_done1)
        # print(new_sell_orders)
        # test if the order mentioned in message_done1 has been removed
        self.assertEqual(
            len(new_sell_orders.get(decimal.Decimal(message_done1['price']))), 1)


        message_done2 = {
            "order_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb",
            "price": "18600.01",
            "product_id": "BTC-USD",
            "reason": "canceled",
            "remaining_size": "99.00",
            "sequence": 46662478162,
            "side": "sell",
            "time": "2022-09-25T02:41:37.594700Z",
            "type": "done"
        }
        print("step 2: handle second done message:{}".format(
            json.dumps(message_done2, indent=4, sort_keys=True)))

        new_sell_orders = ob.done(message_done2)
        # print(new_sell_orders)
        # test if the sell order mentioned in message_done2 does NOT exist any more
        new_orderlist_with_this_price = new_sell_orders.get(decimal.Decimal(message_done2['price']))
        self.assertEqual(new_orderlist_with_this_price, None)
        # self.assertEqual(len(new_orderlist_with_this_price), 1)

        #  test if this sell order's size is in new_sell_orders has been reduced to 1
        # self.assertEqual(new_orderlist_with_this_price[0].get('size'), 1.00)
        print('test_done_order : pass')


    def test_change_order(self):
        """
        'change' means that a resting order has changed size or price
        https://docs.cloud.coinbase.com/exchange/docs/websocket-channels#full-channel
        initial state:
            current 'sell' orders has 3 resting orders
             2 of them: price == 18600.01
            (
             1. order_id='aaa', price = 18600.01, size = 11
             2. order_id='bbb', price = 18600.01, size= 20
            )
            1 of them: price == 18600.02
             order_id='ccc', price = 18600.02, size = 30


             current 'buy' orders has 3 resting orders
             2 of them: price == 18599.99
            (
             1. order_id='ddd', price = 18599.99, size = 40
             2. order_id='eee', price = 18599.99, size= 50
            )
            1 of them: price == 18599.98
             order_id='fff', price = 18599.98, size = 60

        test case:
        1. one sell order with 'change' type and 'STP' reason received, order_id='aaa',
         change its size from old size 11 to new size 22
        2 one buy order with 'change' type and "modify_order' reason  received,
          both price and size have been changed

        test goal:  verify OrderBook.change() method can handle above scenario correctly

        :return:
        """
        print('test change order :')
        ob = OrderBook(["BTC-USD"], ["full"])
        self._initial_order = dict(sell=None, buy=None)
        self._initial_order['sell'] = SortedDict()
        self._initial_order['buy'] = SortedDict()


        print("step 0: initialize both sell and buy order dict:")
        self._initial_order['sell'] = SortedDict({
            decimal.Decimal('18600.01'): [
                {
                    'order_id': 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaa',
                    'size': decimal.Decimal('11.00')
                },
                {
                    'order_id': 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb',
                    'size': decimal.Decimal('20')
                }
            ],
            decimal.Decimal('18600.02'): [
                {
                    'order_id': 'cccccccc-cccc-cccc-cccc-cccccccccc',
                    'size': decimal.Decimal('30')
                }
            ]
        })

        self._initial_order['buy'] = SortedDict({
            decimal.Decimal('18599.99'): [
                {
                    'order_id': 'dddddddd-dddd-dddd-dddd-ddddddddddd',
                    'size': decimal.Decimal('33.00')
                },
                {
                    'order_id': 'eeeeeeee-eeee-eeee-eeee-eeeeeeeeeee',
                    'size': decimal.Decimal('44')
                }
            ],
            decimal.Decimal('18599.98'): [
                {
                    'order_id': 'fffffffffffffffffffffffffffffffffff',
                    'size': decimal.Decimal('55')
                }
            ]
        })

        existing_sell_orders = ob.set_orders('sell', self._initial_order['sell'])
        # print(existing_sell_orders)

        existing_buy_orders = ob.set_orders('buy', self._initial_order['buy'])
        # print(existing_buy_orders)

        message_change1 = {
            "type": "change",
            "reason":"STP",
            "time": "2014-11-07T08:19:27.028459Z",
            "sequence": 80,
            "order_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaa",
            "side": "sell",
            "product_id": "BTC-USD",
            "old_size": "11.00",
            "new_size": "22.22",
            "price": "18600.01"
        }

        print("step 1: handle first change (reason:STP) message:{}".format(
            json.dumps(message_change1, indent=4, sort_keys=True)))

        new_sell_orders = ob.change(message_change1)
        # print(new_sell_orders)

        # test if the order mentioned in message_change1 has been changed accordingly
        new_orderlist_with_this_price = new_sell_orders.get(decimal.Decimal(message_change1['price']))
        self.assertEqual(len(new_orderlist_with_this_price), 2)
        self.assertEqual(new_orderlist_with_this_price[0]['size'], decimal.Decimal(message_change1['new_size']))



        message_change2 ={
            "type": "change",
            "reason":"modify_order",
            "time": "2022-06-06T22:55:43.433114Z",
            "sequence": 24753,
            "order_id": "dddddddd-dddd-dddd-dddd-ddddddddddd",
            "side": "buy",
            "product_id": "BTC-USD",
            "old_size": "33.00",
            "new_size": "333.33",
            "old_price": "18599.99",
            "new_price": "18600.99"
        }

        print("step 2: handle second change( reason:modify_order) message:{}".format(
            json.dumps(message_change2, indent=4, sort_keys=True)))
        new_buy_orders = ob.change(message_change2)
        # print(new_buy_orders)

        new_orderlist_with_this_price = new_buy_orders.get(decimal.Decimal(message_change2['new_price']))
        # test if the new price order has been created
        self.assertNotEqual(new_orderlist_with_this_price, None)
        found = False
        size_changed = False
        for o in new_orderlist_with_this_price:
            if o['order_id'] == message_change2['order_id']:
                found = True
                if o['size'] == decimal.Decimal(message_change2['new_size']):
                    size_changed = True
                break
        self.assertEqual(found, True)
        self.assertEqual(size_changed, True)
        print('test change order : pass')
        # end of testing change message


    def test_match_order(self):
        """
        'match' means that a trade (partial trade) has occurred and an order must be removed
         from the order book (or size updated for partial trade)

        initial state:
            current 'sell' orders has 2 resting orders whose price == 18600.01
            (
             1. order_id='aaa', price = 18600.01, size = 11
             2. order_id='bbb', price = 18600.01, size= 20
            )
        test case:
        1. one sell order with 'match' type message received, maker_order_id='aaa',full match
        2 one sell order with 'match' type message received, maker_order_id='bbb',partial match
        3. one sell order with 'match' type message received, whose price has no match (negative test)
        test goal:  verify OrderBook.match() method can handle above scenario correctly

        :return:
        """
        print('test_match_order :')
        ob = OrderBook(["BTC-USD"], ["full"])
        self._initial_order = dict(sell=None, buy=None)
        self._initial_order['sell'] = SortedDict()


        print("step 0: initialize sell order dict:")
        self._initial_order['sell'] = SortedDict({
            decimal.Decimal('18600.01'): [
                {
                    'order_id': 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaa',
                    'size': decimal.Decimal('11')
                },
                {
                    'order_id': 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb',
                    'size': decimal.Decimal('20')
                }
            ],
            decimal.Decimal('18600.02'): [
                {
                    'order_id': 'cccccccc-cccc-cccc-cccc-cccccccccc',
                    'size': decimal.Decimal('30')
                }
            ]
        })

        existing_sell_orders = ob.set_orders('sell', self._initial_order['sell'])
        # print(existing_sell_orders)


        message_match1 = {
            "maker_order_id": 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaa',
            "price": "18600.01",
            "product_id": "BTC-USD",
            "sequence": 46662479130,
            "side": "sell",
            "size": "11.00",
            "taker_order_id": "1c261649-9819-45c1-bb66-72c92ddab748",
            "time": "2022-09-25T02:41:39.036906Z",
            "trade_id": 417818579,
            "type": "match"
        }

        print("step 1: handle first match message:{}".format(
            json.dumps(message_match1, indent=4, sort_keys=True)))

        new_sell_orders = ob.match(message_match1)
        # print(new_sell_orders)
        # test if the order mentioned in message_match1 has been removed
        new_orderlist_with_this_price = new_sell_orders.get(decimal.Decimal(message_match1['price']))
        self.assertEqual(len(new_orderlist_with_this_price), 1)

        # test if the unmatched order still exist
        self.assertEqual(new_orderlist_with_this_price[0]['order_id'], 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb')
        self.assertEqual(new_orderlist_with_this_price[0]['size'], decimal.Decimal('20'))
        # self.assertEqual()

        message_match2 = {
            "maker_order_id": 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb',
            "price": "18600.01",
            "product_id": "BTC-USD",
            "sequence": 46662479130,
            "side": "sell",
            "size": "10.00",
            "taker_order_id": "3333333-9819-45c1-bb66-72c92ddab748",
            "time": "2022-09-25T02:41:49.036906Z",
            "trade_id": 417818589,
            "type": "match"
        }

        print("step 2: handle second partial match message:{}".format(
            json.dumps(message_match2, indent=4, sort_keys=True)))
        new_sell_orders = ob.match(message_match2)
        # print(new_sell_orders)

        new_orderlist_with_this_price = new_sell_orders.get(decimal.Decimal(message_match2['price']))
        # test if the partial matched order still exist
        self.assertEqual(new_orderlist_with_this_price[0]['order_id'], 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb')
        # test if the partial matched order's remaining size reduced
        self.assertEqual(new_orderlist_with_this_price[0]['size'], decimal.Decimal('20')-decimal.Decimal('10.00'))

        message_match3 = {
            "maker_order_id": 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb',
            "price": "22222.01",
            "product_id": "BTC-USD",
            "sequence": 466333379130,
            "side": "sell",
            "size": "10.00",
            "taker_order_id": "44444444-9819-45c1-bb66-72c92ddab748",
            "time": "2022-09-25T02:42:49.036906Z",
            "trade_id": 417843589,
            "type": "match"
        }

        print("step 3: handle third unknown price match message:{}".format(
            json.dumps(message_match3, indent=4, sort_keys=True)))

        new_sell_orders = ob.match(message_match3)
        # print(new_sell_orders)

        new_orderlist_with_this_price = new_sell_orders.get(decimal.Decimal(message_match2['price']))
        # test if existing orders still exist
        self.assertEqual(new_orderlist_with_this_price[0]['order_id'], 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb')
        # test if order's remaining size does not  change
        self.assertEqual(new_orderlist_with_this_price[0]['size'], decimal.Decimal('20')-decimal.Decimal('10.00'))
        print("test_match_order: pass")



    def test_get_orders_side(self):
        print('test_get_orders_side')
        ob = OrderBook(["BTC-USD", "ETC-USD"], ["full"])
        self.assertDictEqual(ob.get_orders('buy'), SortedDict())
        self.assertDictEqual(ob.get_orders('sell'), SortedDict())
        with self.assertRaises(AssertionError):
            ob.get_orders('bids')
        with self.assertRaises(AssertionError):
            ob.get_orders('asks')
        pass

    def test_initialization(self):
        """
        test OrderBook initialization,

        :return:
        """
        print("test_initialization")
        ob = OrderBook(["BTC-USD", "ETC-USD"], ["full"])
        self.assertDictEqual(ob.get_orders('buy'), SortedDict())
        self.assertDictEqual(ob.get_orders('sell'), SortedDict())
        print("test_initialization: pass")

    def test_get_orders_key(self):
        print("test_get_orders_key")
        ob = OrderBook(["BTC-USD", "ETC-USD"], ["full"])
        with self.assertRaises(AssertionError):
            ob.get_orders('bids')
        with self.assertRaises(AssertionError):
            ob.get_orders('asks')
        print("test_get_orders_key: pass")


if __name__ == '__main__':
    unittest.main()
