#!/usr/bin/env python3

from argparse import ArgumentParser
from typing import override
import traderone as t1
from uniswap import Uniswap



class ConfigKeys():
    PROVIDER = "provider"



class UniswapExchange(t1.Exchange):
    tickers: dict[str, tuple[str, int]] = {
            "eth": ("0x0000000000000000000000000000000000000000", 10**18),
            "bat": ("0x0D8775F648430679A709E98d2b0Cb6250d2887EF", 10**18),
            "dai": ("0x6B175474E89094C44Da98b954EedeAC495271d0F", 10**18),
            }

    def __init__(self, address: str, private_key: str, provider: str, version: int = 2):
        super().__init__("uniswap")
        self.uniswap = Uniswap(address=address, private_key=private_key, version=version, provider=provider)

    def get_address(self) -> str:
        return str(self.uniswap.address)

    def get_auth(self) -> str | None:
        return self.uniswap.private_key

    @override
    def get_supported_tickers(self) -> list[str]:
        return list(self.tickers.keys())

    @override
    def get_exchange_rate(self, from_ticker: str, to_ticker: str) -> float:
        return self.uniswap.get_price_output(self.tickers[from_ticker][0], self.tickers[to_ticker][0], self.tickers[from_ticker][1])/self.tickers[to_ticker][1]

    @override
    def get_fee(self, amount: float, from_wallet: t1.Wallet, to_wallet: t1.Wallet) -> float:
        return self.uniswap.get_fee_taker()

    @override
    def trade(self, amount: float, from_wallet: t1.Wallet, to_wallet: t1.Wallet) -> dict | None:
        out = self.uniswap.make_trade(self.tickers[from_wallet.get_ticker()][0], self.tickers[to_wallet.get_ticker()][0], int(amount*self.tickers[from_wallet.get_ticker()][1]))
        return {"hexbytes": out}

    def get_balance(self, ticker: str):
        return self.uniswap.get_token_balance(self.tickers[ticker][0])


class UniswapWallet(t1.Wallet):
    def __init__(self, ticker: str, exchange: UniswapExchange):
        self.exchange: UniswapExchange = exchange
        super().__init__(ticker, self.exchange.get_address(), self.exchange.get_auth())

    @override
    def get_live_balance(self) -> float | None:
        return self.exchange.get_balance(self.get_ticker())



def run_main(args: dict) -> int:
    exchange: UniswapExchange = UniswapExchange(args[t1.ConfigKeys.ADDRESS], args[t1.ConfigKeys.AUTH], args[ConfigKeys.PROVIDER])
    trader: t1.TraderOne = t1.TraderOne(exchange, [UniswapWallet(ticker, exchange) for ticker in exchange.get_supported_tickers()])
    runner: t1.TraderRunner = t1.TraderRunner(trader)

    return runner.main_loop()


def prep_parser(parser: ArgumentParser | None = None) -> ArgumentParser:
    if parser is None:
        parser = t1.prep_parser()

    parser.add_argument("-p", "--"+ConfigKeys.PROVIDER, help="Provider URL to use")

    return parser



def main(args: list[str]) -> int:
    t1.common_init()
    pargs = t1.parse_args(args, prep_parser())
    return t1.test_main(pargs) if pargs[t1.ConfigKeys.TEST] else run_main(pargs)

if __name__ == "__main__":
    from sys import argv
    exit(main(argv))

