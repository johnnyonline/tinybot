from eth_abi import decode as decode_abi
from web3 import Web3

# Multicall3 — same address on all chains
MULTICALL3 = Web3.to_checksum_address("0xcA11bde05977b3631167028862bE2a173976CA11")
MULTICALL3_ABI = [{
    "name": "aggregate3",
    "type": "function",
    "stateMutability": "payable",
    "inputs": [{"name": "calls", "type": "tuple[]", "components": [
        {"name": "target", "type": "address"},
        {"name": "allowFailure", "type": "bool"},
        {"name": "callData", "type": "bytes"},
    ]}],
    "outputs": [{"name": "returnData", "type": "tuple[]", "components": [
        {"name": "success", "type": "bool"},
        {"name": "returnData", "type": "bytes"},
    ]}],
}]


def multicall(w3: Web3, calls: list) -> list:
    """Batch contract calls. calls = list of ContractFunction objects."""
    mc = w3.eth.contract(address=MULTICALL3, abi=MULTICALL3_ABI)
    encoded = [(call.address, False, call._encode_transaction_data()) for call in calls]
    results = mc.functions.aggregate3(encoded).call()
    decoded = []
    for call, (_, data) in zip(calls, results):
        types = [o["type"] for o in call.abi["outputs"]]
        result = decode_abi(types, data)
        decoded.append(result[0] if len(result) == 1 else result)
    return decoded
