#!/usr/bin/env python3

from logging import getLogger, basicConfig
from threading import Thread
from time import sleep, time
from random import randint


global logger
logger = getLogger("traderone")
logger.setLevel("INFO")


class Transaction():
    TAG_COMPLETED = "completed"


class Wallet():
    def __init__(self, ticker: str, addr: str, auth: str):
        self.ticker: str = ticker
        self.addr: str = addr
        self.auth: str = auth
        self.cached_balance: float = 0
        self.is_refreshing_cached_balance: bool = False

    @staticmethod
    def is_addr_valid(addr: str) -> bool:
        return True

    def get_ticker(self) -> str:
        return self.ticker

    def get_addr(self) -> str:
        return self.addr

    def get_auth(self) -> str:
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

    def tick(self):
        pass

    def do_tick(self):
        delay: float = self.get_min_cycle_delay()
        rand_delay: float = self.get_max_random_cycle_delay_add()
        if rand_delay != 0:
            scale_factor = 100
            delay += randint(0, int(rand_delay*scale_factor))/scale_factor
        current_time: float = time()
        if current_time - self.get_last_tick_time() >= delay:
            self.last_tick_time = current_time
            self.tick()


class TraderOne(Trader):
    def __init__(self, exchange: Exchange, wallets: list[Wallet], min_cycle_delay: float = 30*60, max_random_cycle_delay_add: float = 0, min_proportional_diff: float = 0.1, main_wallet_index: int = 0):
        super().__init__(exchange, wallets, min_cycle_delay, max_random_cycle_delay_add)
        self.min_proportional_diff: float = min_proportional_diff
        self.main_wallet_index: int = main_wallet_index

    def _check_enough_wallets_(self) -> bool:
        w = len(self.get_wallets())
        if w >= 2:
            return True
        else:
            logger.warning(f"Only {w} wallets are set! (At least two(2) are needed)")
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

    def do_trade_cycle(self) -> None:
        main_wallet = self.get_main_wallet()
        if main_wallet is not None:
            wallets = self.get_secondary_wallets()
            if wallets is not None:
                self.refresh_wallets_cached_balances(block=True)
                total_relative_balance: float = 0
                relative_balances: list[tuple[Wallet, float, float]] = []
                for wallet in wallets:
                    rate = self.get_exchange().get_exchange_rate(wallet.get_ticker(), main_wallet.get_ticker())
                    relative_balance = rate*wallet.get_cached_balance()
                    total_relative_balance += relative_balance
                    relative_balances.append((wallet, relative_balance, rate))
                highers: list[tuple[Wallet, float, float]] = []
                lowers: list[tuple[Wallet, float, float]] = []
                num_balances: int = len(relative_balances)+1
                avg_balance: float = total_relative_balance / num_balances
                for wallet, relative_balance, rate in relative_balances:
                    diff_balance: float = relative_balance - avg_balance
                    if diff_balance > 0:
                        highers.append((wallet, diff_balance, rate))
                    elif diff_balance < 0:
                        lowers.append((wallet, diff_balance, rate))
                for stage in [0, 1]:
                    for wallet, diff_balance, rate in highers if stage == 0 else lowers:
                        trade_balance = diff_balance*rate
                        if wallet.get_cached_balance() > 0 and wallet.get_cached_balance() > abs(trade_balance):
                            if abs(trade_balance) / wallet.get_cached_balance() >= self.get_min_proportional_diff():
                                if stage == 0:
                                    if trade_balance > 0:
                                        self.get_exchange().trade(trade_balance, from_wallet=wallet, to_wallet=main_wallet)
                                    else:
                                        if trade_balance < 0:
                                            self.get_exchange().trade(abs(trade_balance), from_wallet=main_wallet, to_wallet=wallet)

    def tick(self):
        self.do_trade_cycle()



class Tests():
    class Test1():
        @staticmethod
        def test1_main(args: list[str], cycles: int = 50) -> int:
            exchange: Tests.Test1.Test1Exchange = Tests.Test1.Test1Exchange()
            trader: TraderOne = TraderOne(exchange, [Tests.Test1.Test1Wallet(ticker, ticker, ticker) for ticker in exchange.get_supported_tickers()], min_cycle_delay=10)
            def printstat():
                logger.info([f"[Ticker: {wallet.get_ticker()}, Address: {wallet.get_addr()}, Auth: {wallet.get_auth()}, LiveBalance: {wallet.get_live_balance()}, CachedBalance: {wallet.get_cached_balance()}, IsRefreshingCachedBalance: {wallet.get_is_refreshing_cached_balance()}]" for wallet in trader.get_wallets() if wallet is not None])
                logger.info(f"Total portfolio value relative to start: {sum([wallet.get_live_balance()*exchange.tickers[trader.get_main_wallet().get_ticker()] for wallet in trader.get_wallets() if wallet is not None])}")
            printstat()
            for n in range(cycles):
                logger.info(f"Starting Cycle no. {n}")
                exchange._shuffle_tickers()
                trader.tick()
                printstat()
                logger.info(f"Finished Cycle no. {n}")
                #sleep(0.1)
            return 0

        class Test1Wallet(Wallet):
            def __init__(self, ticker: str, addr: str, auth: str, start_balance: float = 1):
                super().__init__(ticker, addr, auth)
                self.balance: float = start_balance

            def get_live_balance(self) -> float | None:
                return self.balance

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

            def get_supported_tickers(self) -> list[str]:
                return list(self.tickers.keys())

            def get_exchange_rate(self, from_ticker: str, to_ticker: str) -> float:
                return self.tickers[to_ticker]/self.tickers[from_ticker]

            def trade(self, amount: float, from_wallet: Wallet, to_wallet: Wallet) -> dict | None:
                transaction = from_wallet.send_to("", amount, None)
                if transaction is not None and transaction.get(Transaction.TAG_COMPLETED, False):
                    to_wallet.balance += amount*self.get_exchange_rate(from_wallet.get_ticker(), to_wallet.get_ticker())
                return super().trade(amount, from_wallet, to_wallet)

            def _shuffle_tickers(self):
                for ticker in self.tickers.keys():
                    n = randint(-(self.max_shuffle), self.max_shuffle)
                    if n != 0:
                        self.tickers[ticker] += n
                    if self.tickers[ticker] <= 0:
                        self.tickers[ticker] = 1
                    logger.info(f"Shuffled ticker: {ticker} by {n} to {self.tickers[ticker]}")


def test_main(args: list[str]) -> int:
    basicConfig()
    return Tests.Test1.test1_main(args)#, 1500)


def main(args: list[str]) -> int:
    return 0


if __name__ == "__main__":
    from sys import argv
    #exit(main(argv))
    exit(test_main(argv))

