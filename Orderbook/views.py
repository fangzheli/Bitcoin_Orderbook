
import json
from django.http import HttpResponse
from Orderbook.services import logger
import config

def index(request):
    """
    this function is called whenever client visit http://serverip/data/
    :param request:
    :return:
    """
    # delay importing this object until the thread of Orderbook.apps.background_task has started
    # to create the object inside it.

    data = json.dumps(config.BTC_OrderBook.update_order_books())
    logger.info(data)
    return HttpResponse(data, content_type='application/json')
    pass

