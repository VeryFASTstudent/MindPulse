"""
Async MongoDB connection (Motor driver).

Phase 1 only sets up the connection + a health check. Collection-specific
query logic is added in later phases inside each feature module
(app/auth, app/chat, app/risk_engine, etc.) rather than here, to keep this
file a thin, stable infrastructure layer.
"""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import settings


class MongoDB:
    client: AsyncIOMotorClient | None = None
    db: AsyncIOMotorDatabase | None = None


mongodb = MongoDB()


async def connect_to_mongo() -> None:
    mongodb.client = AsyncIOMotorClient(settings.mongo_uri)
    mongodb.db = mongodb.client[settings.mongo_db_name]
    # Fail fast on startup if the DB is unreachable, instead of failing
    # silently on the first real request.
    await mongodb.client.admin.command("ping")


async def close_mongo_connection() -> None:
    if mongodb.client is not None:
        mongodb.client.close()


def get_database() -> AsyncIOMotorDatabase:
    """
    Dependency-injectable accessor. Later phases import this in their
    routes, e.g.:

        from app.db.mongodb import get_database
        db = get_database()
        await db.users.find_one({"email": email})
    """
    if mongodb.db is None:
        raise RuntimeError("Database not initialized. Did the app startup event run?")
    return mongodb.db
