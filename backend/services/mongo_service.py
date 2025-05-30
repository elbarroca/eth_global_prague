# backend/db/mongodb_utils.py
import os
import pymongo
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
from pymongo.errors import ConnectionFailure, OperationFailure
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

import asyncio

# --- Logging Configuration ---
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)

# --- MongoDB Configuration ---\
MONGO_URI = os.getenv('MONGO_URI')
DATABASE_NAME = os.getenv('DATABASE_NAME')
OHLCV_COLLECTION_NAME = "ohlcv_data"

# Cache durations
CACHE_DURATION_HOURLY_SECONDS = 30 * 60  # 30 minutes (was 1 hour)
CACHE_DURATION_DAILY_SECONDS = 4 * 60 * 60  # 4 hours (was 24 hours)


# --- Pydantic Models for MongoDB Data ---
class OHLVCRecord(BaseModel):
    time: int
    open: float
    high: float
    low: float
    close: float

class StoredOHLCVData(BaseModel):
    chain_id: int
    base_token_address: str
    quote_token_address: str
    period_seconds: int
    timeframe: str # "hourly" or "daily"
    ohlcv_candles: List[OHLVCRecord]
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# --- MongoDB Client ---
mongo_client: Optional[AsyncIOMotorClient] = None
db: Optional[AsyncIOMotorDatabase] = None

async def connect_to_mongo():
    """
    Establishes an asynchronous connection to MongoDB and initializes the database object.
    Creates the collection and necessary indexes if they don't exist.
    """
    global mongo_client, db
    if mongo_client and db:
        try:
            await mongo_client.admin.command('ping')
            logger.info("MongoDB connection already active (async).")
            return # db is already set globally
        except ConnectionFailure:
            logger.warning("MongoDB connection lost (async). Reconnecting...")
            await close_mongo_connection() # Ensure client is closed before reassigning
            mongo_client = None 
            db = None
        except Exception as e: # Catch other potential errors during ping
            logger.warning(f"Error pinging existing MongoDB connection (async): {e}. Reconnecting...")
            await close_mongo_connection()
            mongo_client = None
            db = None


    logger.info(f"Connecting to MongoDB async at {MONGO_URI.split('@')[-1]}...")
    try:
        # Ensure any existing client is closed before creating a new one
        if mongo_client:
            await close_mongo_connection()

        mongo_client = AsyncIOMotorClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        await mongo_client.admin.command('ping') 
        db_instance = mongo_client[DATABASE_NAME] # Assign to local var first
        
        # Atomically assign to global db after successful connection and setup
        db = db_instance
        logger.info(f"Successfully connected to MongoDB async. Database: '{DATABASE_NAME}'")
        
        collection_names = await db.list_collection_names()
        if OHLCV_COLLECTION_NAME not in collection_names:
            logger.info(f"Creating collection '{OHLCV_COLLECTION_NAME}' (async)...")
            await db.create_collection(OHLCV_COLLECTION_NAME)
        
        collection: AsyncIOMotorCollection = db[OHLCV_COLLECTION_NAME]
        
        indexes = await collection.index_information()
        unique_index_name = "ohlcv_unique_query_idx"
        if unique_index_name not in indexes:
            await collection.create_index(
                [
                    ("chain_id", pymongo.ASCENDING),
                    ("base_token_address", pymongo.ASCENDING),
                    ("quote_token_address", pymongo.ASCENDING),
                    ("period_seconds", pymongo.ASCENDING),
                    ("timeframe", pymongo.ASCENDING)  # Add timeframe to unique index
                ],
                name=unique_index_name,
                unique=True
            )
            logger.info(f"Created unique index '{unique_index_name}' on '{OHLCV_COLLECTION_NAME}' (async).")

        last_updated_index_name = "last_updated_idx"
        if last_updated_index_name not in indexes:
            await collection.create_index([("last_updated", pymongo.DESCENDING)], name=last_updated_index_name)
            logger.info(f"Created index '{last_updated_index_name}' on 'last_updated' field (async).")
            
        # No explicit return needed as it sets global 'db'
    except ConnectionFailure as e:
        logger.error(f"MongoDB async connection failed: {e}")
        await close_mongo_connection() # Cleanup
        raise # Re-raise to be caught by startup event
    except OperationFailure as e: 
        logger.error(f"MongoDB async operation failure during connection/setup: {e}")
        await close_mongo_connection() # Cleanup
        raise # Re-raise
    except Exception as e: 
        logger.error(f"Unexpected error during MongoDB async connection/setup: {e}", exc_info=True)
        await close_mongo_connection() # Cleanup
        raise # Re-raise

async def get_ohlcv_from_db(
    chain_id: int,
    base_token_address: str,
    quote_token_address: str,
    period_seconds: int,
    timeframe: str
) -> Optional[List[Dict[str, Any]]]:
    global db 
    if db is None:
        logger.error("Async database connection not available for get_ohlcv_from_db. Connection should be established at startup.")
        # Optionally, you could try to connect here, but it's better handled by startup.
        # await connect_to_mongo() # This might lead to issues if called concurrently
        # if db is None:
        #     logger.error("Failed to connect to DB on demand for get_ohlcv_from_db.")
        #     return None
        return None # Or raise an exception

    collection: AsyncIOMotorCollection = db[OHLCV_COLLECTION_NAME]
    query = {
        "chain_id": chain_id,
        "base_token_address": base_token_address.lower(),
        "quote_token_address": quote_token_address.lower(),
        "period_seconds": period_seconds,
        "timeframe": timeframe  # Add timeframe to match storage structure
    }
    
    logger.debug(f"Querying DB with: {query}")
    
    try:
        document = await collection.find_one(query)
        if document:
            logger.debug(f"Found document in DB: {document.get('_id', 'no_id')} with last_updated: {document.get('last_updated', 'no_timestamp')}")
            stored_data = StoredOHLCVData(**document)
            
            if stored_data.timeframe == "hourly":
                cache_duration = timedelta(seconds=CACHE_DURATION_HOURLY_SECONDS)
            elif stored_data.timeframe == "daily":
                cache_duration = timedelta(seconds=CACHE_DURATION_DAILY_SECONDS)
            else:
                cache_duration = timedelta(seconds=CACHE_DURATION_DAILY_SECONDS)

            last_updated_aware = stored_data.last_updated
            if last_updated_aware.tzinfo is None:
                 last_updated_aware = last_updated_aware.replace(tzinfo=timezone.utc)

            if datetime.now(timezone.utc) - last_updated_aware < cache_duration:
                logger.info(f"Found fresh OHLCV data in DB (async) for {base_token_address}/{quote_token_address} on chain {chain_id} ({timeframe}).")
                return [candle.model_dump() for candle in stored_data.ohlcv_candles]
            else:
                logger.info(f"Found stale OHLCV data in DB (async) for {base_token_address}/{quote_token_address} on chain {chain_id} ({timeframe}). Will re-fetch.")
                return None
        else:
            logger.info(f"No OHLCV data found in DB (async) for {base_token_address}/{quote_token_address} on chain {chain_id} ({timeframe}).")
            return None
    except OperationFailure as e:
        logger.error(f"MongoDB async operation failure during get_ohlcv_from_db: {e}")
        return None
    except Exception as e: 
        logger.error(f"Unexpected error during async get_ohlcv_from_db: {e}", exc_info=True)
        return None

async def store_ohlcv_in_db(
    chain_id: int,
    base_token_address: str,
    quote_token_address: str,
    period_seconds: int,
    timeframe: str,
    ohlcv_candles_data: List[Dict[str, Any]]
):
    global db
    if db is None:
        logger.error("Async database connection not available for store_ohlcv_in_db. Connection should be established at startup.")
        # await connect_to_mongo()
        # if db is None:
        #      logger.error("Failed to connect to DB on demand for store_ohlcv_in_db.")
        #      return
        return


    collection: AsyncIOMotorCollection = db[OHLCV_COLLECTION_NAME]
    
    base_addr_lower = base_token_address.lower()
    quote_addr_lower = quote_token_address.lower()

    parsed_candles = []
    for candle_data in ohlcv_candles_data:
        try:
            parsed_candles.append(OHLVCRecord(
                time=int(candle_data.get("time")),
                open=float(candle_data.get("open")),
                high=float(candle_data.get("high")),
                low=float(candle_data.get("low")),
                close=float(candle_data.get("close"))
            ))
        except (TypeError, ValueError) as e:
            logger.error(f"Skipping invalid candle data during parsing for DB storage (async): {candle_data}. Error: {e}")
            continue

    if not parsed_candles and ohlcv_candles_data:
        logger.warning(f"No valid candles to store for {base_addr_lower}/{quote_addr_lower} (async) after parsing. Original count: {len(ohlcv_candles_data)}")

    document_to_store = StoredOHLCVData(
        chain_id=chain_id,
        base_token_address=base_addr_lower,
        quote_token_address=quote_addr_lower,
        period_seconds=period_seconds,
        timeframe=timeframe,
        ohlcv_candles=parsed_candles,
        last_updated=datetime.now(timezone.utc)
    )
    
    query_filter = {
        "chain_id": chain_id,
        "base_token_address": base_addr_lower,
        "quote_token_address": quote_addr_lower,
        "period_seconds": period_seconds,
        "timeframe": timeframe  # Add timeframe to match unique index
    }
    
    update_data = {"$set": document_to_store.model_dump(by_alias=True)}

    try:
        result = await collection.update_one(query_filter, update_data, upsert=True)
        if result.upserted_id:
            logger.info(f"Inserted new OHLCV data into DB (async) for {base_addr_lower}/{quote_addr_lower} on chain {chain_id} ({timeframe}). ID: {result.upserted_id}")
        elif result.modified_count > 0:
            logger.info(f"Updated existing OHLCV data in DB (async) for {base_addr_lower}/{quote_addr_lower} on chain {chain_id} ({timeframe}).")
        elif result.matched_count > 0 and result.modified_count == 0:
             logger.info(f"OHLCV data for {base_addr_lower}/{quote_addr_lower} on chain {chain_id} ({timeframe}) (async) matched but was identical, no update needed.")
        else:
            logger.warning(f"OHLCV data for {base_addr_lower}/{quote_addr_lower} on chain {chain_id} ({timeframe}) (async) was not inserted or modified. Matched: {result.matched_count}")

    except OperationFailure as e:
        logger.error(f"MongoDB async operation failure during store_ohlcv_in_db: {e}")
        if hasattr(e, 'code') and e.code == 11000: 
            logger.error(f"Duplicate key error (async) despite upsert logic for {base_addr_lower}/{quote_addr_lower}. Check index and query logic. Details: {e.details if hasattr(e, 'details') else 'N/A'}")
    except Exception as e:
        logger.error(f"Unexpected error during async store_ohlcv_in_db: {e}", exc_info=True)

async def close_mongo_connection():
    """Closes the MongoDB connection asynchronously if it's open."""
    global mongo_client, db
    if mongo_client:
        logger.info("Closing MongoDB connection (async).")
        mongo_client.close() # motor client close is synchronous
        mongo_client = None
    # Ensure db is also None if client is None / closed
    db = None