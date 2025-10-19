from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

from pymongo.collection import Collection
from pymongo import MongoClient

from orion.config import settings


class HistoryStore:
    """Persist and retrieve agent interaction histories."""

    def __init__(self, client: Optional[MongoClient] = None):
        self._client = client

    def _get_collection(self) -> Collection:
        if self._client is None:
            self._client = MongoClient(settings.mongodb.uri)

        database = self._client[settings.mongodb.database]
        return database[settings.mongodb.history_collection]

    def save(
        self,
        *,
        user_id: str,
        session_id: str,
        input_text: str,
        answer: str,
        created_at: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        if created_at is None:
            created_at = datetime.utcnow()

        document = {
            "user_id": user_id,
            "session_id": session_id,
            "input": input_text,
            "answer": answer,
            "created_at": created_at,
        }

        collection = self._get_collection()
        collection.insert_one(document)
        return document

    def list(
        self,
        *,
        user_id: str,
        session_id: str,
        order: str = "DESC",
    ) -> List[Dict[str, Any]]:
        if order not in {"ASC", "DESC"}:
            raise ValueError("order must be either 'ASC' or 'DESC'")

        collection = self._get_collection()
        cursor: Iterable[Dict[str, Any]] = collection.find({
            "user_id": user_id,
            "session_id": session_id,
        })

        histories: List[Dict[str, Any]] = []
        for record in cursor:
            histories.append(
                {
                    "user_id": record.get("user_id"),
                    "session_id": record.get("session_id"),
                    "input": record.get("input"),
                    "answer": record.get("answer"),
                    "created_at": record.get("created_at"),
                }
            )

        histories.sort(
            key=lambda item: item.get("created_at") or datetime.min,
            reverse=(order == "DESC"),
        )
        return histories

