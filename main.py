#!/usr/bin/env python

import cbpro
from tradingview_ta import TA_Handler, Interval

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
dip_pct = os.environ.get("CB_DIP_PCT", -5.0)
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


def productBalance(product):
    p = product.split('-')[0]
    return float(next(item for item in auth_client.get_accounts()
                      if item["currency"] == p)["available"])


def executeMarketOrder(product, amount):
    print(f"placing market order for £{amount} of {product}")

    if not debug:
        order = auth_client.place_market_order(product_id=product,
                                               side='buy',
                                               funds=amount)

        if 'id' in order:
            print(f"order id: {order['id']}")
        else:
            print(f"unable to execute:\n{order}")


def sendSms(body):
    client = Client(twilio_sid, twilio_secret)

    client.messages.create(body=body,
                           from_=sms_from,
                           to=sms_to
                           )


def validateProducts(products):
    total = 100
    for product in products.split(','):
        if ':' not in product:
            print(f"{product} is missing percentage, e.g. {product}:50")
            sys.exit(2)
        else:
            total -= int(product.split(':')[1])

    if total:
        print("total percentages do not equal 100")
        sys.exit(2)


def taSummary(product):
    p = product.replace('-', '')
    ta = TA_Handler(
        symbol=p,
        screener="crypto",
        exchange="coinbase",
        interval=Interval.INTERVAL_1_DAY
    )
    summary = ta.get_analysis().summary

    if 'RECOMMENDATION' in summary:
        return summary['RECOMMENDATION']


if __name__ == '__main__':
    executed = {}
    dip = {}
    ta = {}
    validateProducts(products)
    for product in products.split(','):
        executed[product.split(':')[0]] = False
        dip[product.split(':')[0]] = 0.0

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

        for p in products.split(','):
            product = p.split(':')[0]
            product_pct = p.split(':')[1]
            nowtime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            if rem_days < 1:
                daily = format(rem_bal * (int(product_pct) / 100),
                               '.2f')
            else:
                daily = format((rem_bal / rem_days) * (int(product_pct) / 100),
                               '.2f')

            last_order = list(islice(auth_client.get_fills(product_id=product),
                                     1))[0]

            last_order_price = float(last_order['price'])
            cur_price = float(client.get_product_ticker(product_id=product)
                              ["price"])

            price_diff = cur_price - last_order_price
            price_diff_pct = format((price_diff / last_order_price)*100.0,
                                    '.2f')

            ta_advice = taSummary(product)

            if ta_advice == "STRONG_BUY" or ta_advice == "STRONG_SELL":
                if product not in ta or ta_advice != ta[product]:
                    report = f"""
TA report for {product} at {nowtime} is {ta_advice}
Current price is {cur_price}
Last order price was {last_order_price}
"""
                    ta[product] = ta_advice

                    print("*"*30, report)
                    sendSms(report)

            ta_advice = taSummary(product)

            if ta_advice == "STRONG_BUY" or ta_advice == "STRONG_SELL":
                if product not in ta or ta_advice != ta[product]:
                    report = f"""
TA report for {product} at {nowtime} is {ta_advice}
Current price is {cur_price}
Last order price was {last_order_price}
"""
                    ta[product] = ta_advice

                    print("*"*30, report)
                    sendSms(report)

            product_bal = productBalance(product)
            product_bal_gbp = cur_price * product_bal
            if float(price_diff_pct) < float(dip_pct):
                if dip[product] > float(price_diff_pct):
                    dip[product] = float(price_diff_pct)
                    report = f"""
At {nowtime} {product} dipped {price_diff_pct}%
from your last order price ({last_order_price}) to {last_order_price}
current advice is: {ta_advice}
"""
                    print(report)
                    sendSms(report)

            last_order_date = datetime.strptime(last_order['created_at'],
                                                "%Y-%m-%dT%H:%M:%S.%fZ")
            next_order = last_order_date + timedelta(days=1)
            delta = datetime.now() - last_order_date

            if float(daily) < 10.0:
                report = "Insufficient funds"
                print(report)
                sendSms(report)
                sys.exit(1)

            elif delta.days < days:
                if not executed[product]:
                    order = auth_client.get_order(last_order["order_id"])
                    fill_fees = float(order['fill_fees'])
                    filled_size = float(order['filled_size'])
                    executed_value = float(order['executed_value'])

                    report = f"""
last executed {product}
order id: {order['id']}
created at: {order['created_at']}
{order['status']} at: {order['done_at']}
executed value: £{executed_value:.2f}
filled_size: {filled_size}
fill fees: £{fill_fees:.2f}
current holdings: {product_bal} (£{product_bal_gbp:.2f})
next purchase amount: £{daily}
next purchase date: {next_order}
remaining balance: £{rem_bal:.2f}
remaining days: {rem_days}
current advice is: {ta_advice}
"""
                    print("*"*30, report)
                    sendSms(report)
                    executed[product] = True

            else:
                report = f"""
executing {product} order:
remaining balance £{rem_bal:.2f}
remaining days {rem_days}
daily amount {daily}
current price: £{cur_price}
last orders price: £{last_order_price}
price difference: {price_diff:.2f} ({price_diff_pct}%)
current advice is: {ta_advice}
"""
                print("*"*30, report)
                sendSms(report)
                executed[product] = False
                executeMarketOrder(product, daily)

        if debug:
            print(f"sleeping {delay} seconds...")

        time.sleep(int(delay))
