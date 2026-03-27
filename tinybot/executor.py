from eth_account import Account
from eth_account.signers.local import LocalAccount
from web3 import Web3


class Executor:
    def __init__(self, w3: Web3, private_key: str):
        self._w3 = w3
        self._account: LocalAccount = Account.from_key(private_key)

    @property
    def address(self) -> str:
        return self._account.address

    @property
    def balance(self) -> int:
        return self._w3.eth.get_balance(self._account.address)

    def execute(
        self,
        call,
        gas_limit: int = 500_000,
        max_fee_gwei: int = 100,
        max_priority_fee_gwei: int = 3,
        value: int = 0,
        simulate: bool = True,
    ) -> str:
        if simulate:
            call.call({"from": self._account.address, "value": value})

        tx = call.build_transaction(
            {
                "from": self._account.address,
                "nonce": self._w3.eth.get_transaction_count(self._account.address),
                "gas": gas_limit,
                "maxFeePerGas": self._w3.to_wei(max_fee_gwei, "gwei"),
                "maxPriorityFeePerGas": self._w3.to_wei(max_priority_fee_gwei, "gwei"),
                "value": value,
            }
        )
        signed = self._w3.eth.account.sign_transaction(tx, self._account.key)
        tx_hash = self._w3.eth.send_raw_transaction(signed.raw_transaction)
        return tx_hash.hex()
