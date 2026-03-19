from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from web3 import Web3

if TYPE_CHECKING:
    from tinybot.bot import TinyBot

EventHandler = Callable[["TinyBot", Any], Awaitable[None]]
TaskHandler = Callable[["TinyBot"], Awaitable[None]]


@dataclass
class EventListener:
    name: str
    signature: str
    addresses: list[str]
    abi: list[dict[str, Any]]
    handler: EventHandler
    poll_interval: int = 180
    block_buffer: int = 5
    notify_errors: bool = True
    _last_run: float = 0
    _w3: Web3 | None = None

    def add_address(self, address: str) -> None:
        checksummed = self._w3.to_checksum_address(address)  # type: ignore[union-attr]
        if checksummed not in self.addresses:
            self.addresses.append(checksummed)

    def remove_address(self, address: str) -> None:
        checksummed = self._w3.to_checksum_address(address)  # type: ignore[union-attr]
        if checksummed in self.addresses:
            self.addresses.remove(checksummed)


@dataclass
class PeriodicTask:
    name: str
    interval: int
    handler: TaskHandler
    notify_errors: bool = True
    _last_run: float = 0
