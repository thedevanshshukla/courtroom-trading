from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from typing import Protocol

from courtroom_trading.contracts import AuthenticatedUser, DecisionImpact, MemoryBias, MemoryRecord, SystemInput


class DecisionRepository(Protocol):
    async def fetch_bias(self, user_id: str, system_input: SystemInput) -> MemoryBias: ...

    async def store(self, record: MemoryRecord) -> MemoryRecord: ...

    async def update_outcome(
        self,
        user_id: str,
        record_id: str,
        outcome: str,
    ) -> MemoryRecord | None: ...

    async def list_records(self, user_id: str, limit: int = 20) -> list[MemoryRecord]: ...

    async def upsert_user(self, user: AuthenticatedUser) -> dict[str, str]: ...

    async def create_local_user(
        self,
        email: str,
        name: str,
        password_hash: str,
        password_salt: str,
    ) -> dict[str, str] | None: ...

    async def get_local_user_by_email(self, email: str) -> dict[str, str] | None: ...

    async def get_cached_impact(self, user_id: str, cache_key: str) -> DecisionImpact | None: ...

    async def upsert_cache_impact(self, impact: DecisionImpact) -> DecisionImpact: ...

    async def clear_records(self, user_id: str) -> int: ...


def hash_features(system_input: SystemInput) -> str:
    normalized = json.dumps(system_input.to_dict()["features"], sort_keys=True)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def generate_cache_key(system_input: SystemInput) -> str:
    """
    Generate a deterministic cache key from features and signals.
    Bucketizes values to group similar scenarios together.
    
    Example output: "rsi_high|price_above_ma50|ma_bullish|trend_strong|volume_high"
    """
    features = system_input.features
    signals = system_input.derived_signals
    
    # Bucketize RSI into ranges
    rsi_bucket = "unknown"
    if features.rsi < 20:
        rsi_bucket = "very_low"
    elif features.rsi < 40:
        rsi_bucket = "low"
    elif features.rsi < 60:
        rsi_bucket = "mid"
    elif features.rsi < 80:
        rsi_bucket = "high"
    else:
        rsi_bucket = "very_high"
    
    # Bucketize price relative to MAs
    price_bucket = "unknown"
    if features.price < features.ma20:
        price_bucket = "below_ma20"
    elif features.price < features.ma50:
        price_bucket = "between_ma20_ma50"
    else:
        price_bucket = "above_ma50"
    
    # Use signal names directly (already categorized)
    ma_alignment = signals.ma_alignment.lower().replace(" ", "_")
    trend = signals.trend_strength.lower().replace(" ", "_")
    volume_strength = signals.rsi_signal.lower().replace(" ", "_")
    
    cache_key = f"rsi_{rsi_bucket}|price_{price_bucket}|ma_{ma_alignment}|trend_{trend}|volume_{volume_strength}"
    return cache_key


def calculate_bias(records: list[MemoryRecord]) -> MemoryBias:
    if not records:
        return MemoryBias()

    bull_wins = sum(1 for record in records if record.winning_side == "BULL")
    bear_wins = sum(1 for record in records if record.winning_side == "BEAR")
    total = len(records)
    profitable_bull = sum(
        1 for record in records if record.outcome == "PROFIT" and record.winning_side == "BULL"
    )
    profitable_bear = sum(
        1 for record in records if record.outcome == "PROFIT" and record.winning_side == "BEAR"
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


class InMemoryDecisionRepository:
    def __init__(self) -> None:
        self.records: list[MemoryRecord] = []
        self.users: dict[str, dict[str, str]] = {}
        self.local_users: dict[str, dict[str, str]] = {}

    async def fetch_bias(self, user_id: str, system_input: SystemInput) -> MemoryBias:
        feature_hash = hash_features(system_input)
        relevant = [
            record
            for record in self.records
            if record.user_id == user_id and record.features_hash == feature_hash
        ]
        return calculate_bias(relevant)

    async def store(self, record: MemoryRecord) -> MemoryRecord:
        self.records.append(record)
        return record

    async def update_outcome(
        self,
        user_id: str,
        record_id: str,
        outcome: str,
    ) -> MemoryRecord | None:
        for record in self.records:
            if record.user_id == user_id and record.record_id == record_id:
                record.outcome = outcome
                return record
        return None

    async def list_records(self, user_id: str, limit: int = 20) -> list[MemoryRecord]:
        records = [record for record in self.records if record.user_id == user_id]
        ordered = sorted(records, key=lambda item: item.created_at, reverse=True)
        return ordered[:limit]

    async def upsert_user(self, user: AuthenticatedUser) -> dict[str, str]:
        payload = {
            "user_id": user.user_id,
            "email": user.email,
            "name": user.name,
            "picture": user.picture,
            "google_sub": user.google_sub,
        }
        self.users[user.user_id] = payload
        return payload

    async def create_local_user(
        self,
        email: str,
        name: str,
        password_hash: str,
        password_salt: str,
    ) -> dict[str, str] | None:
        email_key = email.strip().lower()
        if email_key in self.local_users:
            return None

        payload = {
            "user_id": f"local:{email_key}",
            "email": email_key,
            "name": name,
            "picture": "",
            "google_sub": "",
            "auth_provider": "local",
            "email_lower": email_key,
            "password_hash": password_hash,
            "password_salt": password_salt,
        }
        self.local_users[email_key] = payload
        self.users[payload["user_id"]] = payload
        return payload

    async def get_local_user_by_email(self, email: str) -> dict[str, str] | None:
        return self.local_users.get(email.strip().lower())

    async def get_cached_impact(self, user_id: str, cache_key: str) -> DecisionImpact | None:
        """Retrieve cached decision impact if it meets confidence threshold."""
        for impact in getattr(self, "_impacts", []):
            if impact.user_id == user_id and impact.cache_key == cache_key:
                # Only return cache if verdict is decisive and we have meaningful confidence
                # Lower threshold (0.0) allows immediate reuse even with low confidence
                # The hit_count tracks how many times this pattern has been seen
                if impact.verdict in ("TRADE", "NO_TRADE") and impact.hit_count >= 1:
                    return impact
        return None

    async def upsert_cache_impact(self, impact: DecisionImpact) -> DecisionImpact:
        """Store or update cached decision impact."""
        if not hasattr(self, "_impacts"):
            self._impacts = []
        
        # Find existing entry
        for i, existing in enumerate(self._impacts):
            if existing.user_id == impact.user_id and existing.cache_key == impact.cache_key:
                # Update hit count and rolling average confidence
                hit_count = existing.hit_count + 1
                avg_confidence = (existing.avg_confidence * existing.hit_count + impact.confidence) / hit_count
                updated = DecisionImpact(
                    cache_key=impact.cache_key,
                    user_id=impact.user_id,
                    verdict=impact.verdict,
                    confidence=impact.confidence,
                    bull_score=impact.bull_score,
                    bear_score=impact.bear_score,
                    hit_count=hit_count,
                    avg_confidence=round(avg_confidence, 3),
                    last_matched=impact.last_matched,
                    created_at=existing.created_at,
                    impact_id=existing.impact_id,
                )
                self._impacts[i] = updated
                return updated
        
        # New entry
        self._impacts.append(impact)
        return impact

    async def clear_records(self, user_id: str) -> int:
        """Clear all decision records for a user. Returns count of deleted records."""
        if not hasattr(self, "_records"):
            self._records = []
        initial_count = len(self._records)
        self._records = [r for r in self._records if r.user_id != user_id]
        return initial_count - len(self._records)


class MongoDecisionRepository:
    def __init__(self, mongodb_uri: str, database_name: str) -> None:
        from pymongo import MongoClient

        self.client = MongoClient(mongodb_uri)
        self.db = self.client[database_name]
        self.records = self.db["decision_records"]
        self.users = self.db["users"]
        self.local_users = self.db["local_users"]
        self.decision_impacts = self.db["decision_impacts"]
        self.records.create_index([("user_id", 1), ("created_at", -1)])
        self.records.create_index([("user_id", 1), ("features_hash", 1)])
        self.users.create_index("google_sub", unique=True)
        self.local_users.create_index("email_lower", unique=True)
        self.decision_impacts.create_index([("user_id", 1), ("cache_key", 1)], unique=True)

    async def fetch_bias(self, user_id: str, system_input: SystemInput) -> MemoryBias:
        feature_hash = hash_features(system_input)
        docs = list(
            self.records.find(
                {"user_id": user_id, "features_hash": feature_hash},
                {"_id": 0},
            )
        )
        records = [MemoryRecord(**doc) for doc in docs]
        return calculate_bias(records)

    async def store(self, record: MemoryRecord) -> MemoryRecord:
        self.records.insert_one(asdict(record))
        return record

    async def update_outcome(
        self,
        user_id: str,
        record_id: str,
        outcome: str,
    ) -> MemoryRecord | None:
        self.records.update_one(
            {"user_id": user_id, "record_id": record_id},
            {"$set": {"outcome": outcome}},
        )
        doc = self.records.find_one({"user_id": user_id, "record_id": record_id}, {"_id": 0})
        return MemoryRecord(**doc) if doc else None

    async def list_records(self, user_id: str, limit: int = 20) -> list[MemoryRecord]:
        docs = list(
            self.records.find({"user_id": user_id}, {"_id": 0})
            .sort("created_at", -1)
            .limit(limit)
        )
        return [MemoryRecord(**doc) for doc in docs]

    async def upsert_user(self, user: AuthenticatedUser) -> dict[str, str]:
        payload = user.to_dict()
        self.users.update_one(
            {"google_sub": user.google_sub},
            {"$set": payload},
            upsert=True,
        )
        return payload

    async def create_local_user(
        self,
        email: str,
        name: str,
        password_hash: str,
        password_salt: str,
    ) -> dict[str, str] | None:
        email_key = email.strip().lower()
        existing = self.local_users.find_one({"email_lower": email_key}, {"_id": 0})
        if existing:
            return None

        payload = {
            "user_id": f"local:{email_key}",
            "email": email_key,
            "name": name,
            "email_lower": email_key,
            "password_hash": password_hash,
            "password_salt": password_salt,
        }
        self.local_users.insert_one(payload)
        return payload

    async def get_local_user_by_email(self, email: str) -> dict[str, str] | None:
        email_key = email.strip().lower()
        user = self.local_users.find_one({"email_lower": email_key}, {"_id": 0})
        return user

    async def get_cached_impact(self, user_id: str, cache_key: str) -> DecisionImpact | None:
        """Retrieve cached decision impact if it meets confidence threshold."""
        doc = self.decision_impacts.find_one(
            {"user_id": user_id, "cache_key": cache_key},
            {"_id": 0},
        )
        if not doc:
            return None
        
        impact = DecisionImpact(**doc)
        # Only return cache if verdict is decisive and we have at least one match
        # Confidence threshold removed to allow reuse of all valid decisions
        if impact.verdict in ("TRADE", "NO_TRADE") and impact.hit_count >= 1:
            return impact
        return None

    async def upsert_cache_impact(self, impact: DecisionImpact) -> DecisionImpact:
        """Store or update cached decision impact."""
        existing_doc = self.decision_impacts.find_one(
            {"user_id": impact.user_id, "cache_key": impact.cache_key},
            {"_id": 0},
        )
        
        if existing_doc:
            # Update with new confidence and hit count
            existing = DecisionImpact(**existing_doc)
            hit_count = existing.hit_count + 1
            avg_confidence = (existing.avg_confidence * existing.hit_count + impact.confidence) / hit_count
            
            updated = DecisionImpact(
                cache_key=impact.cache_key,
                user_id=impact.user_id,
                verdict=impact.verdict,
                confidence=impact.confidence,
                bull_score=impact.bull_score,
                bear_score=impact.bear_score,
                hit_count=hit_count,
                avg_confidence=round(avg_confidence, 3),
                last_matched=impact.last_matched,
                created_at=existing.created_at,
                impact_id=existing.impact_id,
            )
            
            self.decision_impacts.replace_one(
                {"user_id": updated.user_id, "cache_key": updated.cache_key},
                asdict(updated),
            )
            return updated
        else:
            # Insert new impact
            self.decision_impacts.insert_one(asdict(impact))
            return impact

    async def clear_records(self, user_id: str) -> int:
        """Clear all decision records for a user. Returns count of deleted records."""
        result = self.records.delete_many({"user_id": user_id})
        return result.deleted_count
