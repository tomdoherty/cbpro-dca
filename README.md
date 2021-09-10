# cbpro-dca

[Dollar-cost averaging (DCA)](https://www.investopedia.com/terms/d/dollarcostaveraging.asp) is an investment strategy in which an investor divides up the total amount to be invested across periodic purchases of a target asset in an effort to reduce the impact of volatility on the overall purchase. The purchases occur regardless of the asset's price and at regular intervals.

This tool automates the process using [Coinbase Pro](https://pro.coinbase.com).

### Configuration

Configuration is by environment variables:

| Option        | Description                        | Default               |
| :-----------: | :--------------------------------: | :-------------------: |
| CB_DAYS       | Days between executions            | 1                     |
| CB_DEBUG      | Don't execute, output debug info   | false                 |
| CB_DELAY      | Delay between polls                | 3600                  |
| CB_DIP_PCT    | Alert price dips X from last order | -5                    |
| CB_KEY        | API Key                            |                       |
| CB_PASS       | API Password                       |                       |
| CB_PRODUCTS   | Products to DCA. Product:Percent   | BTC-GBP:40,ETH-GBP:60 |
| CB_SECRET     | API Secret                         |                       |
| CB_SMS_FROM   | SMS reports from number            |                       |
| CB_SMS_TO     | SMS reports to number              |                       |
| TWILIO_SECRET | Twilio Secret                      |                       |
| TWILIO_SID    | Twilio SID                         |                       |

### Run in docker

```shell
$ cat env.sh
CB_KEY=XXX
CB_PASS=XXX
CB_SECRET=XXX
CB_PRODUCTS=ETH-GBP:100
CB_DELAY=360

$ docker run --name cbpro-dca --env-file env.sh -d -it tomdo/cbpro-dca
```
