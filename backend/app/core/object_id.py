"""
Shared helper for using MongoDB's ObjectId inside Pydantic v2 models.

Every collection in the blueprint uses ObjectId as its _id. Rather than
re-implementing this conversion in auth, chat, risk_engine, etc., it lives
here once and gets imported everywhere.
"""

from typing import Annotated

from bson import ObjectId
from pydantic import BeforeValidator

# Converts an ObjectId (or a valid ObjectId string) into a plain str so it
# can be safely returned in JSON API responses.
PyObjectId = Annotated[str, BeforeValidator(lambda v: str(v) if isinstance(v, ObjectId) else v)]
