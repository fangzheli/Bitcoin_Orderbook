import React from 'react';
import ReactDOM from "react-dom";
import { OrderBook } from '@lab49/react-order-book';


// This is a simple order book structure. There's an array
// of asks, and array of bids. Each entry in the array is
// an array where the first index represents the price,
// and the second index represents the "size", or the total
// number of units of an asset offered at that price.
// let book = {
//   asks: [
//     ['1.02', '200'],
//     ['1.01', '300'],
//   ],
//   bids: [
//     ['0.99', '5'],
//     ['0.98', '3'],
//   ],
// };

let book = {
    asks: [["19233.63", "0.71772706"], ["19233.62", "0.00488478"], ["19232.77", "0.07"], ["19231.43", "0.14"], ["19231.42", "0.0921495"]],
    bids: [["19227.69", "0.05"], ["19227.48", "0.02417"], ["19227.11", "0.04969543"], ["19226.99", "0.19"], ["19226.97", "0.001"]]
}

function httpGet(theUrl)
{
    var xmlHttp = new XMLHttpRequest();
    xmlHttp.open( "GET", theUrl, false ); // false for synchronous request
    xmlHttp.send( null );
    return xmlHttp.responseText;
}

function pool(){
    //get book
    book = JSON.parse(httpGet('api/data'))
    console.log(book)
    root.render(CoinbaseOrderBook(book))
    // console.log(book)
}
setInterval(pool, 1000);

const root = ReactDOM.createRoot(
  document.getElementById('root')
);

const CoinbaseOrderBook = (book) => {
  return (
    <>
      <style
        // eslint-disable-next-line react/no-danger
        dangerouslySetInnerHTML={{
          __html: `
            .MakeItNiceAgain {
              background-color: #151825;
              color: rgba(255, 255, 255, 0.6);
              display: inline-block;
              font-family: -apple-system, BlinkMacSystemFont, sans-serif;
              font-size: 13px;
              font-variant-numeric: tabular-nums;
              padding: 50px 0;
            }
            .MakeItNiceAgain__side-header {
              font-weight: 700;
              margin: 0 0 5px 0;
              text-align: right;
            }
            .MakeItNiceAgain__list {
              list-style-type: none;
              margin: 0;
              padding: 0;
            }
            .MakeItNiceAgain__list-item {
              border-top: 1px solid rgba(255, 255, 255, 0.1);
              cursor: pointer;
              display: flex;
              justify-content: flex-end;
            }
            .MakeItNiceAgain__list-item:before {
              content: '';
              flex: 1 1;
              padding: 3px 5px;
            }
            .MakeItNiceAgain__side--bids .MakeItNiceAgain__list-item {
              flex-direction: row-reverse;
            }
            .MakeItNiceAgain__side--bids .MakeItNiceAgain__list-item:last-child {
              border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            }
            .MakeItNiceAgain__side--bids .MakeItNiceAgain__size {
              text-align: right;
            }
            .MakeItNiceAgain__list-item:hover {
              background: #262935;
            }
            .MakeItNiceAgain__price {
              border-left: 1px solid rgba(255, 255, 255, 0.1);
              border-right: 1px solid rgba(255, 255, 255, 0.1);
              color: #b7bdc1;
              display: inline-block;
              flex: 0 0 50px;
              margin: 0;
              padding: 3px 5px;
              text-align: center;
            }
            .MakeItNiceAgain__size {
              flex: 1 1;
              margin: 0;
              padding: 3px 5px;
              position: relative;
            }
            .MakeItNiceAgain__size:before {
              background-color: var(--row-color);
              content: '';
              height: 100%;
              left: 0;
              opacity: 0.08;
              position: absolute;
              top: 0;
              width: 100%;
            }
          `,
        }}
      />

      <OrderBook
        book={{ bids: book.bids, asks: book.asks }}
        fullOpacity
        interpolateColor={(color) => color}
        listLength={5}
        stylePrefix="MakeItNiceAgain"
        showSpread={false}
      />
    </>
  );
};
