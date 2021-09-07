#!/usr/bin/env python

import cbpro

import calendar
from datetime import datetime, timedelta
from itertools import islice
import os
import sys
import time

from twilio.rest import Client

key = os.environ.get("CB_KEY")
passphrase = os.environ.get("CB_PASS")
b64secret = os.environ.get("CB_SECRET")
products = os.environ.get("CB_PRODUCTS", "BTC-GBP,ETH-GBP")
delay = os.environ.get("CB_DELAY", 3600)
debug = os.environ.get("CB_DEBUG", False)
days = os.environ.get("CB_DAYS", 1)
sms_to = os.environ.get("CB_SMS_TO")
sms_from = os.environ.get("CB_SMS_FROM")
twilio_sid = os.environ.get("TWILIO_SID")
twilio_secret = os.environ.get("TWILIO_SECRET")


def daysLeftInMonth():
    today = datetime.today()
    last_day = calendar.monthrange(today.year, today.month)[1]

    return float(last_day - today.day)


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


def sendSms(body):
    client = Client(twilio_sid, twilio_secret)

    client.messages.create(body=body,
                           from_=sms_from,
                           to=sms_to
                           )


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

        rem_bal = remainingBalance()
        rem_days = daysLeftInMonth()
        total_products = len(products.split(','))

        if rem_days < 1:
            daily = rem_bal
        else:
            daily = format((rem_bal / rem_days) / total_products, '.2f')

        for product in products.split(','):
            last_order = list(islice(auth_client.get_fills(product_id=product),
                                     1))[0]

            last_order_price = float(last_order['price'])
            cur_price = float(client.get_product_ticker(product_id=product)
                              ["price"])

            price_diff = cur_price - last_order_price
            price_diff_pct = (price_diff / last_order_price)*100.0

            last_order_date = datetime.strptime(last_order['created_at'],
                                                "%Y-%m-%dT%H:%M:%S.%fZ")
            next_order = last_order_date + timedelta(days=1)
            delta = datetime.now() - last_order_date

            if rem_bal < 5:
                if not insufficient_funds:
                    report = "Insufficient funds"
                    print(report)
                    sendSms(report)
                    insufficient_funds = True

            elif delta.days < days:
                if not executed[product]:
                    order = auth_client.get_order(last_order["order_id"])

                    report = f"""
executed {product}
order id: {order['id']}
created at: {order['created_at']}
done at: {order['done_at']}
executed value: {order['executed_value']}
filled_size: {order['filled_size']}
fill fees: {order['fill_fees']}
status: {order['status']}
next purchase amount/date: {daily}/{next_order}
remaining balance/days: {rem_bal:.2f}/{rem_days}
current price: {cur_price}
last orders price: {last_order_price}
price difference: {price_diff:.2f} ({price_diff_pct:.2f}%)
"""
                    print("*"*30, report)
                    sendSms(report)
                    executed[product] = True

                insufficient_funds = False

            else:
                report = f"""
executing {product} order:
remaining balance {rem_bal}
remaining days {rem_days}
daily amount {daily}
"""
                print("*"*30, report)
                sendSms(report)
                executed[product] = False
                executeMarketOrder(product, daily)

        if debug:
            print(f"sleeping {delay} seconds...")

        time.sleep(int(delay))
