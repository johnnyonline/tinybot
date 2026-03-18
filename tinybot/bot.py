import asyncio
import time
from datetime import datetime
from typing import Any

from web3 import Web3

from tinybot.executor import Executor
from tinybot.state import State
from tinybot.tg import DEV_GROUP_CHAT_ID, notify_group_chat
from tinybot.types import EventHandler, EventListener, PeriodicTask, TaskHandler
from tinybot.utils import event_id, event_signature


class TinyBot:
    def __init__(self, rpc_url: str, name: str = "tinybot", private_key: str = ""):
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.name = name
        self.state = State()
        self.executor = Executor(self.w3, private_key) if private_key else None
        self._listeners: list[EventListener] = []
        self._tasks: list[PeriodicTask] = []

    # -------------------------------------------------------------------------
    # Registration
    # -------------------------------------------------------------------------

    def listen(
        self,
        name: str,
        event: str,
        addresses: list[str],
        abi: list[dict[str, Any]],
        handler: EventHandler,
        poll_interval: int = 180,
        block_buffer: int = 5,
        notify_errors: bool = False,
    ) -> EventListener:
        if not addresses:
            raise ValueError(f"listener '{name}': addresses cannot be empty")
        if any(listener.name == name for listener in self._listeners):
            raise ValueError(f"listener '{name}' already registered")

        signature = event_signature(abi, event)

        listener = EventListener(
            name=name,
            signature=signature,
            addresses=[self.w3.to_checksum_address(a) for a in addresses],
            abi=abi,
            handler=handler,
            poll_interval=poll_interval,
            block_buffer=block_buffer,
            notify_errors=notify_errors,
            _w3=self.w3,
        )
        self._listeners.append(listener)
        return listener

    def every(
        self,
        interval: int,
        handler: TaskHandler,
        name: str = "",
        notify_errors: bool = False,
    ) -> PeriodicTask:
        task = PeriodicTask(
            name=name or handler.__name__,
            interval=interval,
            handler=handler,
            notify_errors=notify_errors,
        )
        self._tasks.append(task)
        return task

    # -------------------------------------------------------------------------
    # Getters
    # -------------------------------------------------------------------------

    def get_listener(self, name: str) -> EventListener:
        for listener in self._listeners:
            if listener.name == name:
                return listener
        raise ValueError(f"listener '{name}' not found")

    # -------------------------------------------------------------------------
    # Replay
    # -------------------------------------------------------------------------

    async def replay(self, name: str, from_block: int, to_block: int) -> None:
        listener = self.get_listener(name)
        print(f"[{self.name}] replaying '{name}' from {from_block} to {to_block}...")
        await self._process_logs(listener, from_block, to_block)
        print(f"[{self.name}] replay '{name}' done")

    # -------------------------------------------------------------------------
    # Polling
    # -------------------------------------------------------------------------

    async def _handle_error(self, e: Exception, name: str, notify: bool) -> None:
        print(f"[{name}] error: {e}")
        if notify:
            await notify_group_chat(f"❌ [{name}] {e}", chat_id=DEV_GROUP_CHAT_ID)

    async def _process_logs(self, listener: EventListener, from_block: int, to_block: int) -> None:
        topic = self.w3.keccak(text=listener.signature)
        decoder = self.w3.eth.contract(address=listener.addresses[0], abi=listener.abi)
        event_name = listener.signature.split("(")[0]

        raw_logs = self.w3.eth.get_logs(
            {
                "fromBlock": from_block,
                "toBlock": to_block,
                "address": listener.addresses,
                "topics": [topic],
            }
        )

        for raw_log in raw_logs:
            event = getattr(decoder.events, event_name)()
            log = event.process_log(raw_log)
            eid = event_id(log)
            if self.state.is_processed(eid):
                continue
            await listener.handler(self, log)
            self.state.mark_processed(eid)

    async def _poll_listener(self, listener: EventListener) -> None:
        now = time.time()
        if now - listener._last_run < listener.poll_interval:
            return
        listener._last_run = now

        try:
            current_block: int = self.w3.eth.block_number
            last = self.state.last_block.get(listener.name, 0)
            from_block = last - listener.block_buffer if last else current_block

            if from_block >= current_block:
                self.state.last_block[listener.name] = current_block
                return

            await self._process_logs(listener, from_block, current_block)
            self.state.last_block[listener.name] = current_block
        except Exception as e:
            await self._handle_error(e, listener.name, listener.notify_errors)

    async def _poll_task(self, task: PeriodicTask) -> None:
        now = time.time()
        if now - task._last_run < task.interval:
            return
        task._last_run = now

        try:
            await task.handler(self)
        except Exception as e:
            await self._handle_error(e, task.name, task.notify_errors)

    # -------------------------------------------------------------------------
    # Run
    # -------------------------------------------------------------------------

    async def run(self, tick: int = 10) -> None:
        await notify_group_chat(
            f"🟢 <b>{self.name} started</b>",
            chat_id=DEV_GROUP_CHAT_ID,
        )

        while True:
            print(f"[{self.name}] polling... {datetime.now()}")
            for listener in self._listeners:
                await self._poll_listener(listener)
            for task in self._tasks:
                await self._poll_task(task)
            await asyncio.sleep(tick)
