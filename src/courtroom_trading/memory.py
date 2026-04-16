from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from courtroom_trading.contracts import MemoryBias, MemoryRecord, SystemInput


class JsonMemoryStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("[]", encoding="utf-8")

    def _load(self) -> list[MemoryRecord]:
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        normalized: list[MemoryRecord] = []
        for item in payload:
            item.setdefault("outcome", "PENDING")
            normalized.append(MemoryRecord(**item))
        return normalized

    def _save(self, records: list[MemoryRecord]) -> None:
        payload = [asdict(record) for record in records]
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def hash_features(self, system_input: SystemInput) -> str:
        normalized = json.dumps(system_input.to_dict()["features"], sort_keys=True)
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]

    def fetch_bias(self, system_input: SystemInput) -> MemoryBias:
        records = self._load()
        feature_hash = self.hash_features(system_input)
        similar = [record for record in records if record.features_hash == feature_hash]
        if not similar:
            return MemoryBias()

        bull_wins = sum(1 for record in similar if record.winning_side == "BULL")
        bear_wins = sum(1 for record in similar if record.winning_side == "BEAR")
        total = len(similar)
        profitable_bull = sum(
            1
            for record in similar
            if record.outcome == "PROFIT" and record.winning_side == "BULL"
        )
        profitable_bear = sum(
            1
            for record in similar
            if record.outcome == "PROFIT" and record.winning_side == "BEAR"
        )

        historical_bias = "NEUTRAL"
        if profitable_bull > profitable_bear:
            historical_bias = "BULL"
        elif profitable_bear > profitable_bull:
            historical_bias = "BEAR"

        return MemoryBias(
            bull_weight=round((bull_wins + 1) / (total + 2), 3),
            bear_weight=round((bear_wins + 1) / (total + 2), 3),
            historical_outcome_bias=historical_bias,
            similar_cases=total,
        )

    def store(self, record: MemoryRecord) -> MemoryRecord:
        records = self._load()
        records.append(record)
        self._save(records)
        return record

    def update_outcome(self, record_id: str, outcome: str) -> MemoryRecord | None:
        records = self._load()
        updated: MemoryRecord | None = None
        for record in records:
            if record.record_id == record_id:
                record.outcome = outcome
                updated = record
                break

        if updated is not None:
            self._save(records)
        return updated
