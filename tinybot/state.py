class State:
    def __init__(self):
        self.last_block: dict[str, int] = {}  # listener_name -> block
        self.active_items: list = []
        self._processed: set = set()

    def is_processed(self, event_id: str) -> bool:
        return event_id in self._processed

    def mark_processed(self, event_id: str):
        self._processed.add(event_id)

    def add_item(self, *addrs: str):
        item = list(addrs)
        if item not in self.active_items:
            self.active_items.append(item)

    def remove_item(self, item: list):
        if item in self.active_items:
            self.active_items.remove(item)
