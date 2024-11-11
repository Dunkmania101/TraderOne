#!/usr/bin/env python3

from argparse import ArgumentParser
from logging import getLogger, basicConfig
from threading import Thread
from time import sleep, time
from random import randint
from typing import final, override



class LoggerWrapper: # This is here just in case regular print statements are needed
    def __init__(self, name: str = "traderone"):
        self.logger = getLogger(name)
        self.logger.setLevel("INFO")

    def info(self, msg):
        self.logger.info(msg)
        #print(msg)

    def warning(self, msg):
        self.logger.warning(msg)
        #print(msg)

    def error(self, msg):
        self.logger.error(msg)
        #print(msg)


global logger
logger = LoggerWrapper()



def get_div_str(end: bool = False, thin: bool = False) -> str:
    begincap = "++"
    endcap = "--"
    body = "__________" if thin else "=========="
    cap, title = (endcap, "END") if end else (begincap, "BEGIN")
    return cap+body+title+body+cap


@final
class ConfigKeys():
    ADDRESS = "address"
    AUTH = "auth"
    TRADER = "trader"
    EXCHANGE = "exchange"
    TEST = "test"
    CYCLES = "cycles"


@final
class Transaction():
    TAG_COMPLETED = "completed"


class Wallet():
    def __init__(self, ticker: str, addr: str, auth: str | None):
        self.ticker: str = ticker
        self.addr: str = addr
        self.auth: str | None = auth
        self.cached_balance: float = 0
        self.is_refreshing_cached_balance: bool = False

    @staticmethod
    def is_addr_valid(addr: str) -> bool:
        return True

    def get_ticker(self) -> str:
        return self.ticker

    def get_addr(self) -> str:
        return self.addr

    def get_auth(self) -> str | None:
        return self.auth

    def get_cached_balance(self) -> float:
        return self.cached_balance

    def get_live_balance(self) -> float | None:
        return 0

    def get_is_refreshing_cached_balance(self) -> bool:
        return self.is_refreshing_cached_balance

    def refresh_cached_balance(self, block: bool = True) -> None:
        if block:
            self.is_refreshing_cached_balance = True
            balance = self.get_live_balance()
            if balance is not None:
                self.cached_balance = balance
            self.is_refreshing_cached_balance = False
        else:
            Thread(target=self.refresh_cached_balance, kwargs={"block": True}).start()

    def send_to(self, rec_addr: str, amount: float | None, meta: dict | None) -> dict | None:
        return {Transaction.TAG_COMPLETED: True}


class Exchange():
    def __init__(self, title: str):
        self.title: str = title

    def get_title(self) -> str:
        return self.title

    def get_supported_tickers(self) -> list[str]:
        return []

    def get_exchange_rate(self, from_ticker: str, to_ticker: str) -> float:
        return 0

    def get_fee(self, amount: float, from_wallet: Wallet, to_wallet: Wallet) -> float:
        return 0

    def trade(self, amount: float, from_wallet: Wallet, to_wallet: Wallet) -> dict | None:
        pass


class Trader():
    def __init__(self, exchange: Exchange, wallets: list[Wallet], min_cycle_delay: float = 30*60, max_random_cycle_delay_add: float = 0):
        self.exchange: Exchange = exchange
        self.wallets: list[Wallet] = wallets
        self.min_cycle_delay: float = min_cycle_delay
        self.max_random_cycle_delay_add: float = max_random_cycle_delay_add
        self.last_tick_time: float = 0

    def get_exchange(self) -> Exchange:
        return self.exchange

    def get_wallets(self) -> list[Wallet]:
        return self.wallets

    def refresh_wallets_cached_balances(self, block: bool = True) -> None:
        for wallet in self.get_wallets():
            wallet.refresh_cached_balance(block=False)
        if block:
            while any(wallet.get_is_refreshing_cached_balance() for wallet in self.get_wallets() if wallet is not None):
                sleep(0.1)

    def get_min_cycle_delay(self) -> float:
        return self.min_cycle_delay

    def get_max_random_cycle_delay_add(self) -> float:
        return self.max_random_cycle_delay_add

    def get_last_tick_time(self) -> float:
        return self.last_tick_time

    def is_runnable(self) -> bool:
        return True

    def do_trade_cycle(self):
        pass

    def tick(self):
        delay: float = self.get_min_cycle_delay()
        rand_delay: float = self.get_max_random_cycle_delay_add()
        if rand_delay != 0:
            float_scale = 100
            delay += randint(0, int(rand_delay*float_scale))/float_scale
        current_time: float = time()
        if current_time - self.get_last_tick_time() >= delay:
            self.last_tick_time = current_time
            self.do_trade_cycle()


class TraderRunner():
    def __init__(self, trader: Trader):
        self.trader: Trader = trader

    def main_loop(self, cycles: int | None = -1, pause: float = 0.1) -> int:
        def printstat():
            logger.info([f"[Ticker: {wallet.get_ticker()}, Address: {wallet.get_addr()}, Auth: {wallet.get_auth()}, LiveBalance: {wallet.get_live_balance()}, CachedBalance: {wallet.get_cached_balance()}, IsRefreshingCachedBalance: {wallet.get_is_refreshing_cached_balance()}]" for wallet in self.trader.get_wallets() if wallet is not None])
            #logger.info(f"Total portfolio value change relative to start: {sum([wallet.get_live_balance()*exchange.tickers[trader.get_main_wallet().get_ticker()] for wallet in trader.get_wallets() if wallet is not None])}")
        printstat()
        def run(n: int):
            logger.info(get_div_str(False, False))
            logger.info(f"Starting Cycle no. {n}")
            logger.info(get_div_str(False, True))
            self.trader.do_trade_cycle()
            printstat()
            logger.info(f"Finished Cycle no. {n}")
            logger.info(get_div_str(True, False))
            sleep(pause)
        if cycles is not None and cycles > -1:
            for n in range(cycles):
                run(n)
        else:
            n = 0
            while True:
                try:
                    run(n)
                    n += 1
                except KeyboardInterrupt:
                    print("Keyboard interrupt received, exiting...")
                    break
        return 0




class TraderOne(Trader):
    def __init__(self, exchange: Exchange, wallets: list[Wallet], min_cycle_delay: float = 30*60, max_random_cycle_delay_add: float = 0, min_proportional_diff: float = 0.1, max_downs: int | None = 100, main_wallet_index: int = 0):
        super().__init__(exchange, wallets, min_cycle_delay, max_random_cycle_delay_add)
        self.min_proportional_diff: float = min_proportional_diff
        self.main_wallet_index: int = main_wallet_index
        self.down_tracker: list[tuple[float | None, int]] = [(None, 0) for _ in self.get_wallets()]
        self.max_downs: int | None = max_downs

    def _check_enough_wallets_(self) -> bool:
        w = len(self.get_wallets())
        if w >= 2:
            return True
        else:
            logger.warning(f"Only {w} wallet{'' if w == 1 else 's'} {'is' if w == 1 else 'are'} set! (At least two(2) are needed)")
            return False

    def get_min_proportional_diff(self) -> float:
        return self.min_proportional_diff

    def get_main_wallet_index(self) -> int:
        return self.main_wallet_index

    def get_main_wallet(self) -> Wallet | None:
        if self._check_enough_wallets_():
            return self.get_wallets()[self.get_main_wallet_index()]
        else:
            return None

    def get_secondary_wallets(self) -> list[Wallet] | None:
        if self._check_enough_wallets_():
            wallets = self.get_wallets().copy()
            wallets.pop(self.get_main_wallet_index())
            return wallets
        else:
            return None

    @override
    def do_trade_cycle(self) -> None:
        main_wallet = self.get_main_wallet()
        if main_wallet is not None:
            wallets = self.get_secondary_wallets()
            if wallets is not None:
                self.refresh_wallets_cached_balances(block=True)
                total_relative_balance: float = 0
                relative_balances: list[tuple[Wallet, float, float]] = []
                for i, wallet in enumerate(wallets):
                    rate = self.get_exchange().get_exchange_rate(wallet.get_ticker(), main_wallet.get_ticker())
                    if self.down_tracker[i][0] is not None:
                        since_up = self.down_tracker[i][1] + 1 if self.down_tracker[i][0] < rate else 0
                    else:
                        since_up = 0
                    self.down_tracker[i] = (rate, since_up)
                    relative_balance = rate*wallet.get_cached_balance()
                    total_relative_balance += relative_balance
                    relative_balances.append((wallet, relative_balance, rate))
                highers: list[tuple[Wallet, float, float]] = []
                lowers: list[tuple[Wallet, float, float]] = []
                num_balances: int = len(relative_balances)+1
                avg_balance: float = total_relative_balance / num_balances
                for i, bal in enumerate(relative_balances):
                    wallet, relative_balance, rate = bal
                    if self.max_downs is not None and self.down_tracker[i][1] > self.max_downs:
                        logger.warning(f"Ticker {wallet.get_ticker()} has been down for {self.down_tracker[i][1]} trade-cycles, skipping...")
                        pass
                    diff_balance: float = relative_balance - avg_balance
                    if diff_balance > 0:
                        highers.append((wallet, diff_balance, rate))
                    elif diff_balance < 0:
                        lowers.append((wallet, diff_balance, rate))
                for stage in (0, 1):
                    for wallet, diff_balance, rate in highers if stage == 0 else lowers:
                        trade_balance = diff_balance*rate
                        if wallet.get_cached_balance() > 0 and wallet.get_cached_balance() > abs(trade_balance):
                            if (abs(trade_balance)+self.get_exchange().get_fee(trade_balance, main_wallet if stage else wallet, wallet if stage else main_wallet)) / wallet.get_cached_balance() >= self.get_min_proportional_diff():
                                if stage == 0:
                                    if trade_balance > 0:
                                        self.get_exchange().trade(trade_balance, from_wallet=wallet, to_wallet=main_wallet)
                                    else:
                                        if trade_balance < 0:
                                            self.get_exchange().trade(abs(trade_balance), from_wallet=main_wallet, to_wallet=wallet)



class Tests():
    class Test1():
        @staticmethod
        def test1_main(args: dict, cycles: int = 50) -> int:
            exchange: Tests.Test1.Test1Exchange = Tests.Test1.Test1Exchange()
            trader: TraderOne = TraderOne(exchange, [Tests.Test1.Test1Wallet(ticker, ticker, ticker) for ticker in exchange.get_supported_tickers()], min_cycle_delay=10)
            def printstat():
                logger.info([f"[Ticker: {wallet.get_ticker()}, Address: {wallet.get_addr()}, Auth: {wallet.get_auth()}, LiveBalance: {wallet.get_live_balance()}, CachedBalance: {wallet.get_cached_balance()}, IsRefreshingCachedBalance: {wallet.get_is_refreshing_cached_balance()}]" for wallet in trader.get_wallets() if wallet is not None])
                logger.info(f"Total portfolio value change relative to start: {sum([wallet.get_live_balance()*exchange.tickers[trader.get_main_wallet().get_ticker()] for wallet in trader.get_wallets() if wallet is not None])}")
            printstat()
            def run(n: int):
                logger.info(get_div_str(False, False))
                logger.info(f"Starting Cycle no. {n}")
                logger.info(get_div_str(False, True))
                exchange.shuffle_tickers()
                logger.info(get_div_str(True, True))
                #trader.tick()
                trader.do_trade_cycle()
                printstat()
                logger.info(f"Finished Cycle no. {n}")
                logger.info(get_div_str(True, False))
                #sleep(0.1)
            if cycles > -1:
                for n in range(cycles):
                    run(n)
            else:
                n = 0
                while True:
                    try:
                        run(n)
                        n += 1
                    except KeyboardInterrupt:
                        print("Keyboard interrupt received, exiting...")
                        break
            return 0

        class Test1Wallet(Wallet):
            def __init__(self, ticker: str, addr: str, auth: str, start_balance: float = 1):
                super().__init__(ticker, addr, auth)
                self.balance: float = start_balance

            @override
            def get_live_balance(self) -> float | None:
                return self.balance

            @override
            def send_to(self, rec_addr: str, amount: float | None, meta: dict | None) -> dict | None:
                if amount is not None:
                    newbalance = self.balance - amount
                    if newbalance < 0:
                        return {Transaction.TAG_COMPLETED: False}
                    else:
                        self.balance = newbalance
                return super().send_to(rec_addr, amount, meta)

        class Test1Exchange(Exchange):
            def __init__(self, name: str = "test", num_tickers: int = 6, max_shuffle: int = 3):
                super().__init__(name)
                self.tickers: dict[str, float] = {}
                for n in range(num_tickers):
                    self.tickers[str(n)] = n
                self.max_shuffle: int = max_shuffle

            @override
            def get_supported_tickers(self) -> list[str]:
                return list(self.tickers.keys())

            @override
            def get_exchange_rate(self, from_ticker: str, to_ticker: str) -> float:
                return self.tickers[to_ticker]/self.tickers[from_ticker]

            @override
            def trade(self, amount: float, from_wallet: Wallet, to_wallet: Wallet) -> dict | None:
                transaction = from_wallet.send_to("", amount, None)
                if transaction is not None and transaction.get(Transaction.TAG_COMPLETED, False):
                    to_wallet.balance += amount*self.get_exchange_rate(from_wallet.get_ticker(), to_wallet.get_ticker())
                return super().trade(amount, from_wallet, to_wallet)

            @override
            def get_fee(self, amount: float, from_wallet: Wallet, to_wallet: Wallet) -> float:
                return self.get_exchange_rate(from_wallet.get_ticker(), to_wallet.get_ticker())*(randint(1, 10)/100)

            def shuffle_tickers(self):
                for ticker in self.tickers.keys():
                    n = randint(-(self.max_shuffle), self.max_shuffle)
                    #n = -0.001 # To validate that down-stopping works
                    if n != 0:
                        self.tickers[ticker] += n
                    if self.tickers[ticker] <= 0:
                        self.tickers[ticker] = 1
                    logger.info(f"Shuffled ticker: {ticker} by {n} to {self.tickers[ticker]}")


def test_main(args: dict) -> int:
    return Tests.Test1.test1_main(args, cycles=args.get(ConfigKeys.CYCLES, -1))

def run_main(args: dict) -> int:
    logger.error("This is the base script; no live exchanges/wallets are defined here! You must run a script that extends this one to perform live trading. traderone-uniswap.py is provided as an example. Exiting with error code 1...")
    return 1



def common_init() -> None:
    from sys import stdout
    basicConfig(stream=stdout)
    #basicConfig()


def prep_parser(parser: ArgumentParser | None = None) -> ArgumentParser:
    if parser is None:
        parser = ArgumentParser()

    parser.add_argument("-w", "--"+ConfigKeys.ADDRESS, help="Wallet address to use")
    parser.add_argument("-a", "--"+ConfigKeys.AUTH, help="Wallet authentication token to use (most likely a private key)")
    parser.add_argument("-e", "--"+ConfigKeys.EXCHANGE, help="Name of exchane to use (CURRENTLY UNUSED)")
    parser.add_argument("-t", "--"+ConfigKeys.TRADER, help="Name of trader to use (CURRENTLY UNUSED)")
    parser.add_argument("-T", "--"+ConfigKeys.TEST, help="Test mode", action="store_true")
    parser.add_argument("-c", "--"+ConfigKeys.CYCLES, help="Number of cycles to complete (unspecified or -1 for unlimited)", type=int, default=-1)

    return parser


def parse_args(args: list[str], parser: ArgumentParser | None = None) -> dict:
    if parser is None:
        parser = prep_parser()

    pargs = vars(parser.parse_args(args=args[1:]))

    return pargs

def main(args: list[str]) -> int:
    common_init()
    pargs = parse_args(args)
    return test_main(pargs) if pargs[ConfigKeys.TEST] else run_main(pargs)


if __name__ == "__main__":
    from sys import argv
    exit(main(argv))

