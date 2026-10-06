from core.errors import InvalidSave
from core.game.snapshot import GameSnapshot
from core.save import codec, storage
from core.views.slot_view import SlotView
from core.save.storage import MAX_SLOTS


class SaveStore:
    def _check_slot(self, slot: int) -> None:
        if not isinstance(slot, int) or isinstance(slot, bool) or not 1 <= slot <= MAX_SLOTS:
            raise InvalidSave(f"Numéro de slot invalide : {slot!r}")

    def save(self, slot: int, snapshot: GameSnapshot) -> None:
        self._check_slot(slot)
        storage.write(slot, codec.encode(snapshot))

    def load(self, slot: int) -> GameSnapshot:
        self._check_slot(slot)
        return codec.decode(storage.read(slot))   # lève InvalidSave

    def list_slots(self) -> list[int]:
        return storage.slots()
    
    def list_slots_info(self) -> tuple[SlotView, ...]:
        infos = []
        for slot in range(1, MAX_SLOTS + 1):
            if slot not in storage.slots():
                infos.append(SlotView(slot=slot, name=None, level=None,
                                    location=None, saved_at=None))
                continue
            try:
                data = storage.read(slot)
                meta = data["meta"]
                infos.append(SlotView(
                    slot=slot,
                    name=meta["name"],
                    level=meta["level"],
                    location=meta["location"],
                    saved_at=data["saved_at"],
                ))
            except (InvalidSave, KeyError, TypeError):
                infos.append(SlotView(slot=slot, name=None, level=None,
                                    location=None, saved_at=None, readable=False))
        return tuple(infos)

    def delete(self, slot: int) -> None:
        self._check_slot(slot)
        storage.delete(slot)
