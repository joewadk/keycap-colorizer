from math import isclose

from app.models.compatibility import CompatibilityResult, KeyFitIssue
from app.models.keyboard import KeyboardDefinition, KeyboardKey
from app.models.keycap import KeycapSet, SupportedKey


def normalize_legend(legend: str) -> str:
    value = "".join(character for character in legend.casefold() if character.isalnum())
    return {
        "control": "ctrl", "escape": "esc", "spacebar": "space", "": "space",
        "pageup": "pgup", "pagedown": "pgdn", "pgdown": "pgdn",
        "delete": "del", "insert": "ins", "capslock": "caps",
        "windows": "win", "function": "fn",
    }.get(value, value) if value or not legend.strip() else legend.strip()


def fits(key: KeyboardKey, cap: SupportedKey) -> bool:
    return isclose(key.width_u, cap.width_u, abs_tol=1e-6, rel_tol=0) and (
        cap.legend is None or normalize_legend(key.legend) == normalize_legend(cap.legend)
    )


def check_compatibility(keyboard: KeyboardDefinition, kit: KeycapSet) -> CompatibilityResult:
    if not kit.supported_keys:
        return CompatibilityResult(
            status="unknown", compatible=False,
            warnings=["This keycap set has no key inventory. Fit cannot be verified."],
        )

    # Each slot represents one physical cap. Unknown quantities are potential
    # matches, never proof of compatibility; cap expansion is bounded by demand.
    slots = [
        cap
        for cap in sorted(kit.supported_keys, key=lambda cap: cap.quantity is None)
        for _ in range(min(cap.quantity or len(keyboard.keys), len(keyboard.keys)))
    ]
    candidates = {
        index: [slot for slot, cap in enumerate(slots) if fits(key, cap)]
        for index, key in enumerate(keyboard.keys) if key.height_u == 1
    }
    owners: dict[int, int] = {}

    def assign(key_index: int, visited: set[int]) -> bool:
        for slot in candidates[key_index]:
            if slot in visited:
                continue
            visited.add(slot)
            if slot not in owners or assign(owners[slot], visited):
                owners[slot] = key_index
                return True
        return False

    for key_index in sorted(candidates, key=lambda index: len(candidates[index])):
        assign(key_index, set())
    allocations = {key_index: slot for slot, key_index in owners.items()}
    missing: list[KeyFitIssue] = []
    uncertain: list[KeyFitIssue] = []
    for index, key in enumerate(keyboard.keys):
        details = {"key": key.id, "required_width_u": key.width_u}
        if key.height_u != 1:
            uncertain.append(KeyFitIssue(**details, reason="Kit inventory does not specify key heights."))
        elif index not in allocations:
            reason = "Not enough matching keycaps." if candidates[index] else "No matching size and legend in the supplied inventory."
            missing.append(KeyFitIssue(**details, reason=reason))
        elif slots[allocations[index]].quantity is None:
            uncertain.append(KeyFitIssue(**details, reason="Matching keycap quantity is unspecified."))

    status = "incompatible" if missing else "unknown" if uncertain else "compatible"
    return CompatibilityResult(
        status=status, compatible=status == "compatible", missing=missing, uncertain=uncertain,
        warnings=["Checks use the supplied sizes, legends, and quantities only. Stem fit and row profile are not verified."],
    )
