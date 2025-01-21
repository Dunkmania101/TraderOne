#!/usr/bin/env python3

from argparse import ArgumentParser
from typing import final#, override
import asyncio
import traderone as t1
from agentipy import SolanaAgentKit, AgentiConstants
from solders.pubkey import Pubkey



@final
class ConfigKeys():
    PROVIDER = "provider"



async def f(l):
    out = await l()
    return out


class SolanaExchange(t1.Exchange):
    tickers: dict[str, Pubkey] = AgentiConstants.TOKENS

    def __init__(self, private_key: str, provider: str | None = None, slippage: int = AgentiConstants.DEFAULT_OPTIONS["SLIPPAGE_BPS"]):
        super().__init__("solana")
        self.agent = SolanaAgentKit(private_key, provider)
        self.private_key: str = private_key
        self.slippage: int = slippage

    def get_address(self) -> str:
        return str(self.agent.wallet_address)

    def get_auth(self) -> str | None:
        return self.private_key

    #@override
    def get_supported_tickers(self) -> list[str]:
        return list(self.tickers.keys())

    #@override
    def get_exchange_rate(self, from_ticker: str, to_ticker: str) -> float:
        return f(lambda: self.agent.fetch_price(from_ticker)) / f(lambda: self.agent.fetch_price(to_ticker))

    #@override
    def get_fee(self, amount: float, from_wallet: t1.Wallet, to_wallet: t1.Wallet) -> float:
        return self.slippage

    #@override
    def trade(self, amount: float, from_wallet: t1.Wallet, to_wallet: t1.Wallet) -> dict | None:
        out = f(lambda: self.agent.trade(Pubkey.from_string(self.tickers[to_wallet.get_ticker()]), amount, Pubkey.from_string(self.tickers[self.from_wallet.get_ticker()]), slippage_bps=self.get_fee()))
        return {"hexbytes": out}

    def get_balance(self, ticker: str):
        return f(lambda: self.agent.get_balance(self.tickers[ticker]))



class SolanaWallet(t1.Wallet):
    def __init__(self, ticker: str, exchange: SolanaExchange):
        self.exchange: SolanaExchange = exchange
        super().__init__(ticker, self.exchange.get_address(), self.exchange.get_auth())

    #@override
    def get_live_balance(self) -> float | None:
        return self.exchange.get_balance(self.get_ticker())



async def run_main(args: dict) -> int:
    exchange: SolanaExchange = SolanaExchange(args[t1.ConfigKeys.AUTH], args[ConfigKeys.PROVIDER])
    trader: t1.TraderOne = t1.TraderOne(exchange, [SolanaWallet(ticker, exchange) for ticker in exchange.get_supported_tickers()])
    runner: t1.TraderRunner = t1.TraderRunner(trader)

    return runner.main_loop()


def prep_parser(parser: ArgumentParser | None = None) -> ArgumentParser:
    if parser is None:
        parser = t1.prep_parser()

    parser.add_argument("-p", "--"+ConfigKeys.PROVIDER, help="Provider URL to use")

    return parser



async def main(args: list[str]) -> int:
    t1.common_init()
    pargs = t1.parse_args(args, prep_parser())
    return t1.test_main(pargs) if pargs[t1.ConfigKeys.TEST] else run_main(pargs)

if __name__ == "__main__":
    from sys import argv
    exit(asyncio.run(main(argv)))

