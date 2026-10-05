from eth_abi import decode as decode_abi
from eth_utils import get_abi_output_types
from web3 import Web3

# Multicall3 — same address on all chains
MULTICALL3 = Web3.to_checksum_address("0xcA11bde05977b3631167028862bE2a173976CA11")
MULTICALL3_ABI = [
    {
        "name": "aggregate3",
        "type": "function",
        "stateMutability": "payable",
        "inputs": [
            {
                "name": "calls",
                "type": "tuple[]",
                "components": [
                    {"name": "target", "type": "address"},
                    {"name": "allowFailure", "type": "bool"},
                    {"name": "callData", "type": "bytes"},
                ],
            }
        ],
        "outputs": [
            {
                "name": "returnData",
                "type": "tuple[]",
                "components": [
                    {"name": "success", "type": "bool"},
                    {"name": "returnData", "type": "bytes"},
                ],
            }
        ],
    }
]


def multicall(w3: Web3, calls: list, allow_failure: bool = False, batch_size: int = 200) -> list:
    """Batch contract calls. calls = list of ContractFunction objects.

    With allow_failure=True, a reverting call (or one that returns no data) yields None instead of
    reverting the whole batch. Calls are sent in chunks of batch_size to stay under eth_call gas caps.
    """
    mc = w3.eth.contract(address=MULTICALL3, abi=MULTICALL3_ABI)
    decoded = []
    for i in range(0, len(calls), batch_size):
        chunk = calls[i : i + batch_size]
        encoded = [(call.address, allow_failure, call._encode_transaction_data()) for call in chunk]
        results = mc.functions.aggregate3(encoded).call()
        for call, (success, data) in zip(chunk, results):
            if allow_failure and (not success or not data):
                decoded.append(None)
                continue
            try:
                result = decode_abi(get_abi_output_types(call.abi), data)
            except Exception:
                if not allow_failure:
                    raise
                decoded.append(None)
                continue
            decoded.append(result[0] if len(result) == 1 else result)
    return decoded
