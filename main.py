#!/usr/bin/env python

import cbpro

import calendar
from datetime import datetime, timedelta
from itertools import islice
import os
import sys
import time

key = os.environ.get("CB_KEY")
passphrase = os.environ.get("CB_PASS")
b64secret = os.environ.get("CB_SECRET")
products = os.environ.get("CB_PRODUCTS", "BTC-GBP,ETH-GBP")
delay = os.environ.get("CB_DELAY", 3600)
debug = os.environ.get("CB_DEBUG", False)
days = os.environ.get("CB_DAYS", 1)


def daysLeftInMonth():
    today = datetime.today()
    last_day = calendar.monthrange(today.year, today.month)[1]

    return float((last_day - today.day) + 1)


def remainingBalance():
    return float(next(item for item in auth_client.get_accounts()
                      if item["currency"] == "GBP")["available"])


def executeMarketOrder(product, amount):
    print(f"placing market order for £{amount} of {product}")

    if not debug:
        order = auth_client.place_market_order(product_id=product,
                                               side='buy',
                                               funds=amount)

        print(f"order id: {order['id']}")


if __name__ == '__main__':
    executed = {}
    insufficient_funds = False
    for product in products.split(','):
        executed[product] = False
    if not key:
        print("[ERROR]: CB_KEY not set")
        sys.exit(1)

    if not b64secret:
        print("[ERROR]: CB_SECRET not set")
        sys.exit(1)

    if not passphrase:
        print("[ERROR]: CB_PASS not set")
        sys.exit(1)

    if not products:
        print("[ERROR]: CB_PRODUCTS not set")
        sys.exit(1)

    print(f"Running DCA for {products} every {days} days")
    while True:
        client = cbpro.PublicClient()
        auth_client = cbpro.AuthenticatedClient(key, b64secret, passphrase)

        today = datetime.now().strftime("%F")
        rem_bal = remainingBalance()
        rem_days = daysLeftInMonth()
        total_products = len(products.split(','))

        daily = format((rem_bal / rem_days) / total_products, '.2f')
        for product in products.split(','):

            last_order = list(islice(auth_client.get_fills(product_id=product),
                                     1))[0]

            last_order_date = datetime.strptime(last_order['created_at'],
                                                "%Y-%m-%dT%H:%M:%S.%fZ")
            next_order = last_order_date + timedelta(days=1)
            delta = datetime.utcnow() - last_order_date

            if rem_bal < 5:
                if not insufficient_funds:
                    print("Insufficient funds")
                    insufficient_funds = True

            elif delta.days < days:
                if not executed[product]:
                    order = auth_client.get_order(last_order["order_id"])
                    print("*"*30)
                    print(f"already executed {product} today")
                    print(f"order id: {order['id']}")
                    print(f"created at: {order['created_at']}")
                    print(f"done at: {order['done_at']}")
                    print(f"executed value: {order['executed_value']}")
                    print(f"filled_size: {order['filled_size']}")
                    print(f"fill fees: {order['fill_fees']}")
                    print(f"status: {order['status']}")
                    print(f"next purchase amount/date: {daily}/{next_order}")
                    print(f"remaining balance/days: {rem_bal:.2f}/{rem_days}")
                    print("*"*30)
                    executed[product] = True

                insufficient_funds = False

            else:
                print("*"*30)
                print(f"executing {product} order:")
                print(f"remaining balance {rem_bal}")
                print(f"remaining days {rem_days}")
                print(f"daily amount {daily}")

                executed[product] = False
                executeMarketOrder(product, daily)

                print("*"*30)

        if debug:
            print(f"sleeping {delay} seconds...")

        time.sleep(int(delay))
