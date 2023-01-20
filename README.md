# Coinbase Orderbook # 
## 1. Tech stack: ##   
* frontend: react using https://github.com/lab49/react-order-book to build component   
* backend: using Python Django   

## 2. Code: ##
* The main logic of maintaining orderbook is in Coinbase_Orderbook/Orderbook/services.py. There is a class of WebsocketClient to maintain the websocket connection with Coinbase API and a class of OrderBook as a subclass of WebsocketClient, which implemented all the message handlers.   
* The unit tests for class OrderBook are in Coinbase_Orderbook/Orderbook/tests.py. Unit tests are mocked for open, done, change and match. I also tried to compare the output of coinbase L2-orderbook and my version L2-orderbook but I am running out of time to implement it for now.   
* The lock case is checked through an assert statement in update_order_books() in Coinbase_Orderbook/Orderbook/services.py   
* The two main endpoints is /orderbook, which is the UI. and /orderbook/api/data, which is the api for front-end to fetch data.  
* The console of the backend will output the live orderbook in the format of sample shown in pdf.   

## 3. Run: ##
* The main program can be run through 'python manage.py runserver' in command line in folder Coinbase_Orderbook.   
* The UI can be accessed by visiting http://127.0.0.1:8000/orderbook/   

## 4. Known issue: ##
* It sometimes take a long time to initialize the order book from rest API of coinbase and orderbook is not available at that time, detail can be seen in  reset_OrderBook() in Coinbase_Orderbook/Orderbook/services.py. Through the console log, it can be seen if it is ready.   
* Not finishing the comparison between coinbase L2-orderbook API and my version L2-orderbook from full orderbook.   

## 5. Author: ##  
Fangzhe Li   
