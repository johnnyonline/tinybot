# tinybot

Minimal Python framework for building crypto bots.

## Installation

```bash
pip install tinybot
```

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `BOT_ACCESS_TOKEN` | Yes | Telegram bot token |
| `GROUP_CHAT_ID` | Yes | Telegram group for notifications |
| `ERROR_GROUP_CHAT_ID` | Yes | Telegram group for errors and startup |
| `PRIVATE_KEY` | No | Private key for onchain execution |

## Quick Start

```python
import asyncio
import os
from tinybot import TinyBot, multicall, notify_group_chat

ERC20_ABI = [...]
STRATEGY_ABI = [...]

async def on_transfer(bot, log):
    print(f"{log.args.sender} -> {log.args.receiver}: {log.args.value}")
    await notify_group_chat(f"Transfer from {log.args.sender}")

async def check_and_tend(bot):
    strategy = bot.w3.eth.contract(address="0x...", abi=STRATEGY_ABI)
    needs_tend, _ = strategy.functions.tendTrigger().call()
    if needs_tend:
        tx_hash = bot.executor.execute(
            strategy.functions.tend(),
            gas_limit=5_000_000,
        )
        await notify_group_chat(f"Tend submitted: {tx_hash}")

async def main():
    bot = TinyBot(
        rpc_url=os.environ["RPC_URL"],
        name="my bot",
        private_key=os.environ.get("PRIVATE_KEY", ""),
    )

    bot.listen(
        name="transfers",
        event="Transfer",
        addresses=["0x..."],
        abi=ERC20_ABI,
        handler=on_transfer,
        poll_interval=180,
        notify_errors=True,
    )

    bot.every(3600, check_and_tend, notify_errors=True)

    await bot.run()

asyncio.run(main())
```

## API

### `TinyBot(rpc_url, name="tinybot", private_key="")`

Creates a bot instance.

- `bot.w3` — `web3.Web3` instance
- `bot.state` — `State` instance (see below)
- `bot.executor` — `Executor` instance if `private_key` is provided, else `None`
- `bot.name` — used in logs and Telegram startup message

On `run()`, sends a startup message to `ERROR_GROUP_CHAT_ID` and prints a polling heartbeat every tick.

---

### `bot.listen(...) -> EventListener`

Register an event listener.

```python
bot.listen(
    name="kicks",            # unique name
    event="AuctionKicked",   # event name (must exist in ABI)
    addresses=["0x..."],     # contracts to monitor
    abi=[...],               # ABI containing the event
    handler=on_kick,         # async fn(bot, log)
    poll_interval=180,       # seconds between polls (default: 180)
    block_buffer=5,          # re-scan buffer in blocks (default: 5)
    notify_errors=True,      # send errors to Telegram (default: False)
)
```

The event signature is derived from the ABI at registration time. Raises `ValueError` if:
- Event not found in ABI
- Duplicate listener name
- Empty addresses

---

### `bot.every(interval, handler, name="", notify_errors=False) -> PeriodicTask`

Register a periodic task.

```python
bot.every(3600, check_expired, notify_errors=True)
```

Handler signature: `async fn(bot)`

---

### `bot.get_listener(name) -> EventListener`

Get a registered listener by name. Raises `ValueError` if not found.

---

### `bot.replay(name, from_block, to_block)`

Replay historical events through a listener's handler. Useful for testing with real chain data.

```python
await bot.replay("kicks", from_block=21000000, to_block=21000500)
```

---

### `bot.run(tick=10)`

Start the polling loop. `tick` (default: 10s) is the inner loop sleep. Each listener and task fires at its own interval.

---

### `EventListener`

Returned by `bot.listen()`.

- `listener.add_address(address)` — add a contract address at runtime
- `listener.remove_address(address)` — remove a contract address at runtime

Both handle checksumming and dedup.

---

### `Executor`

Available via `bot.executor` when `private_key` is provided.

```python
bot = TinyBot(rpc_url, name="my bot", private_key=os.environ["PRIVATE_KEY"])

tx_hash = bot.executor.execute(
    contract.functions.tend(strategy_addr),
    gas_limit=5_000_000,
    max_fee_gwei=100,
    max_priority_fee_gwei=3,
)
```

- `executor.address` — signer address
- `executor.balance` — signer ETH balance in wei
- `executor.execute(call, ...)` — sign and broadcast a transaction, returns tx hash immediately (fire and forget)

---

### `State`

In-memory state, available via `bot.state`.

- `state.last_block` — `dict[str, int]` mapping names to last processed block
- `state.active_items` — `list` of tracked items (e.g. address pairs)
- `state.add_item(*addrs)` — add an item (deduped)
- `state.remove_item(item)` — remove an item
- `state.is_processed(event_id)` — check if event was processed
- `state.mark_processed(event_id)` — mark event as processed (handled automatically for listeners)

---

### `multicall(w3, calls) -> list`

Batch contract reads via [Multicall3](https://github.com/mds1/multicall).

```python
symbol, decimals = multicall(bot.w3, [
    token.functions.symbol(),
    token.functions.decimals(),
])
```

---

### `notify_group_chat(text, parse_mode="HTML", chat_id=GROUP_CHAT_ID)`

Send a Telegram message. HTML parse mode by default.

---

### `event_id(log) -> str`

Unique ID from a log (`txHash:logIndex`). Used internally for dedup, also available for custom event processing in periodic tasks.

## Handler Signatures

```python
# Event handler
async def on_event(bot: TinyBot, log) -> None: ...

# Task handler
async def my_task(bot: TinyBot) -> None: ...
```

Access `bot.w3`, `bot.state`, `bot.executor`, and `bot.get_listener()` from any handler.

## Error Handling

When `notify_errors=True`, exceptions are caught and sent to `ERROR_GROUP_CHAT_ID` as `[name] error message`. The bot continues running.
