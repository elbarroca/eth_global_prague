# backend/db/mongodb_utils.py
import os
import pymongo
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
from pymongo.errors import ConnectionFailure, OperationFailure
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional, Tuple
from models import OHLVCRecord, StoredOHLCVData, PortfolioWeights, StoredPortfolioData, ForecastSignalRecord, CrossChainPortfolioResponse, StoredCrossChainPortfolioData
from pandas import Series as pd_Series, DataFrame as pd_DataFrame
import pandas as pd
from pydantic import BaseModel, Field
from dotenv import load_dotenv

import asyncio

# Load environment variables from .env file
load_dotenv()

# --- Logging Configuration ---
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)

# --- MongoDB Configuration ---
MONGO_URI = os.getenv('MONGO_URI')
DATABASE_NAME = os.getenv('DATABASE_NAME')

# Validate required environment variables
if not MONGO_URI:
    raise ValueError("MONGO_URI environment variable is not set. Please check your .env file.")
if not DATABASE_NAME:
    raise ValueError("DATABASE_NAME environment variable is not set. Please check your .env file.")
OHLCV_COLLECTION_NAME = "ohlcv_data"
PORTFOLIO_COLLECTION_NAME = "portfolio_cache"
FORECAST_SIGNALS_COLLECTION_NAME = "forecast_signals"
CROSS_CHAIN_PORTFOLIO_COLLECTION_NAME = "cross_chain_portfolio_cache"

# Cache durations
CACHE_DURATION_HOURLY_SECONDS = 30 * 60  # 30 minutes (was 1 hour)
CACHE_DURATION_DAILY_SECONDS = 4 * 60 * 60  # 4 hours (was 24 hours)
CACHE_DURATION_PORTFOLIO_SECONDS = 2 * 60 * 60  # 2 hours for portfolio cache
CACHE_DURATION_CROSS_CHAIN_SECONDS = 1 * 60 * 60 # 1 hour for cross-chain portfolio cache

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


    # Additional safety check
    if not MONGO_URI:
        raise ValueError("MONGO_URI is not configured. Please check your environment variables.")
    
    # Log connection attempt (hide credentials)
    try:
        connection_display = MONGO_URI.split('@')[-1] if '@' in MONGO_URI else "localhost"
    except Exception:
        connection_display = "configured database"
    
    logger.info(f"Connecting to MongoDB async at {connection_display}...")
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
        
        if PORTFOLIO_COLLECTION_NAME not in collection_names:
            logger.info(f"Creating collection '{PORTFOLIO_COLLECTION_NAME}' (async)...")
            await db.create_collection(PORTFOLIO_COLLECTION_NAME)
        
        if FORECAST_SIGNALS_COLLECTION_NAME not in collection_names:
            logger.info(f"Creating collection '{FORECAST_SIGNALS_COLLECTION_NAME}' (async)...")
            await db.create_collection(FORECAST_SIGNALS_COLLECTION_NAME)
        
        if CROSS_CHAIN_PORTFOLIO_COLLECTION_NAME not in collection_names:
            logger.info(f"Creating collection '{CROSS_CHAIN_PORTFOLIO_COLLECTION_NAME}' (async)...")
            await db.create_collection(CROSS_CHAIN_PORTFOLIO_COLLECTION_NAME)
        
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
        
        # Create indexes for portfolio collection
        portfolio_collection: AsyncIOMotorCollection = db[PORTFOLIO_COLLECTION_NAME]
        portfolio_indexes = await portfolio_collection.index_information()
        
        portfolio_unique_index_name = "portfolio_unique_query_idx"
        if portfolio_unique_index_name not in portfolio_indexes:
            await portfolio_collection.create_index(
                [
                    ("chain_id", pymongo.ASCENDING),
                    ("timeframe", pymongo.ASCENDING),
                    ("mvo_objective", pymongo.ASCENDING),
                    ("risk_free_rate", pymongo.ASCENDING),
                    ("annualization_factor", pymongo.ASCENDING)
                ],
                name=portfolio_unique_index_name,
                unique=True
            )
            logger.info(f"Created unique index '{portfolio_unique_index_name}' on '{PORTFOLIO_COLLECTION_NAME}' (async).")

        portfolio_last_updated_index_name = "portfolio_last_updated_idx"
        if portfolio_last_updated_index_name not in portfolio_indexes:
            await portfolio_collection.create_index([("last_updated", pymongo.DESCENDING)], name=portfolio_last_updated_index_name)
            logger.info(f"Created index '{portfolio_last_updated_index_name}' on portfolio 'last_updated' field (async).")
            
        # Create indexes for forecast_signals collection
        forecast_signals_collection: AsyncIOMotorCollection = db[FORECAST_SIGNALS_COLLECTION_NAME]
        forecast_signals_indexes = await forecast_signals_collection.index_information()
        
        forecast_signal_unique_index_name = "forecast_signal_unique_idx"
        if forecast_signal_unique_index_name not in forecast_signals_indexes:
            await forecast_signals_collection.create_index(
                [
                    ("asset_symbol", pymongo.ASCENDING),
                    ("chain_id", pymongo.ASCENDING),
                    ("signal_type", pymongo.ASCENDING),
                    ("timeframe", pymongo.ASCENDING),
                    ("forecast_timestamp", pymongo.DESCENDING)
                ],
                name=forecast_signal_unique_index_name,
                unique=True
            )
            logger.info(f"Created unique index '{forecast_signal_unique_index_name}' on '{FORECAST_SIGNALS_COLLECTION_NAME}' (async).")

        forecast_signal_last_updated_index_name = "forecast_signal_last_updated_idx"
        if forecast_signal_last_updated_index_name not in forecast_signals_indexes:
            await forecast_signals_collection.create_index([("last_updated", pymongo.DESCENDING)], name=forecast_signal_last_updated_index_name)
            logger.info(f"Created index '{forecast_signal_last_updated_index_name}' on forecast_signals 'last_updated' field (async).")
            
        # Create indexes for cross_chain_portfolio_cache collection
        cross_chain_portfolio_collection: AsyncIOMotorCollection = db[CROSS_CHAIN_PORTFOLIO_COLLECTION_NAME]
        cross_chain_portfolio_indexes = await cross_chain_portfolio_collection.index_information()
        
        cross_chain_portfolio_unique_index_name = "cross_chain_portfolio_unique_query_idx"
        if cross_chain_portfolio_unique_index_name not in cross_chain_portfolio_indexes:
            await cross_chain_portfolio_collection.create_index(
                [
                    ("request_chain_ids_str", pymongo.ASCENDING),
                    ("request_timeframe", pymongo.ASCENDING),
                    ("request_max_tokens_per_chain", pymongo.ASCENDING),
                    ("request_mvo_objective", pymongo.ASCENDING),
                    ("request_risk_free_rate", pymongo.ASCENDING),
                    ("request_annualization_factor_override", pymongo.ASCENDING),
                    ("request_target_return", pymongo.ASCENDING)
                ],
                name=cross_chain_portfolio_unique_index_name,
                unique=True # Ensure request parameter combination is unique for a cache entry
            )
            logger.info(f"Created unique index '{cross_chain_portfolio_unique_index_name}' on '{CROSS_CHAIN_PORTFOLIO_COLLECTION_NAME}' (async).")

        cross_chain_portfolio_last_updated_index_name = "cross_chain_portfolio_last_updated_idx"
        if cross_chain_portfolio_last_updated_index_name not in cross_chain_portfolio_indexes:
            await cross_chain_portfolio_collection.create_index([("last_updated", pymongo.DESCENDING)], name=cross_chain_portfolio_last_updated_index_name)
            logger.info(f"Created index '{cross_chain_portfolio_last_updated_index_name}' on cross_chain_portfolio_cache 'last_updated' field (async).")
            
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
) -> Optional[Dict[str, Any]]:
    global db 
    if db is None:
        logger.error("Async database connection not available for get_ohlcv_from_db. Connection should be established at startup.")
        return None

    collection: AsyncIOMotorCollection = db[OHLCV_COLLECTION_NAME]
    query = {
        "chain_id": chain_id,
        "base_token_address": base_token_address.lower(),
        "quote_token_address": quote_token_address.lower(),
        "period_seconds": period_seconds,
        "timeframe": timeframe
    }
    
    logger.debug(f"Querying DB with: {query}")
    
    try:
        document = await collection.find_one(query)
        if document:
            logger.debug(f"Found document in DB: {document.get('_id', 'no_id')} with last_updated: {document.get('last_updated', 'no_timestamp')}")
            stored_data = StoredOHLCVData(**document)
            
            latest_candle_timestamp_in_db: Optional[int] = None
            if stored_data.ohlcv_candles:
                # Assuming candles are sorted by time, get the last one's time
                latest_candle_timestamp_in_db = stored_data.ohlcv_candles[-1].time

            # Determine the effective cache duration for this specific timeframe
            # This duration is for the service to consider data "fresh enough" for its own short-term caching logic
            # The 24-hour logic will be handled by the caller.
            if stored_data.timeframe in ["hourly", "min15", "min5", "hour4"]: # More frequent updates for shorter timeframes
                internal_cache_duration_seconds = CACHE_DURATION_HOURLY_SECONDS
            else: # "daily", "week", "month"
                internal_cache_duration_seconds = CACHE_DURATION_DAILY_SECONDS
            
            cache_duration = timedelta(seconds=internal_cache_duration_seconds)

            last_updated_aware = stored_data.last_updated
            if last_updated_aware.tzinfo is None:
                 last_updated_aware = last_updated_aware.replace(tzinfo=timezone.utc)

            is_fresh_short_term = (datetime.now(timezone.utc) - last_updated_aware < cache_duration)
            
            status = "fresh" if is_fresh_short_term else "stale_short_term"
            
            logger.info(f"OHLCV data in DB for {base_token_address}/{quote_token_address} on chain {chain_id} ({timeframe}) is {status}. Last updated: {last_updated_aware}. Latest candle ts: {latest_candle_timestamp_in_db}")
            return {
                "status": status,
                "data": [candle.model_dump() for candle in stored_data.ohlcv_candles],
                "last_updated": last_updated_aware, # Return the actual last_updated timestamp
                "raw_document": document, # For potential advanced merging later
                "latest_candle_timestamp_in_db": latest_candle_timestamp_in_db,
                "base_token_symbol": stored_data.base_token_symbol,
                "quote_token_symbol": stored_data.quote_token_symbol,
                "chain_name": stored_data.chain_name,
            }
        else:
            logger.info(f"No OHLCV data found in DB (async) for {base_token_address}/{quote_token_address} on chain {chain_id} ({timeframe}).")
            return None # No data at all
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
    ohlcv_candles_data: List[Dict[str, Any]],
    base_token_symbol: str,
    quote_token_symbol: str,
    chain_name: str,
    latest_known_timestamp_in_db: Optional[int] = None
):
    global db
    if db is None:
        logger.error("Async database connection not available for store_ohlcv_in_db.")
        return

    collection: AsyncIOMotorCollection = db[OHLCV_COLLECTION_NAME]
    
    base_addr_lower = base_token_address.lower()
    quote_addr_lower = quote_token_address.lower()

    parsed_api_candles = []
    for candle_data in ohlcv_candles_data:
        try:
            timestamp_value = candle_data.get("timestamp") or candle_data.get("time")
            if timestamp_value is None:
                logger.error(f"Skipping API candle data with missing timestamp/time field: {candle_data}")
                continue
            
            parsed_api_candles.append(OHLVCRecord(
                time=int(timestamp_value),
                open=float(candle_data.get("open")),
                high=float(candle_data.get("high")),
                low=float(candle_data.get("low")),
                close=float(candle_data.get("close"))
            ))
        except (TypeError, ValueError) as e:
            logger.error(f"Skipping invalid API candle data during parsing: {candle_data}. Error: {e}")
            continue
    
    # Sort API candles by time just in case, essential for filtering
    parsed_api_candles.sort(key=lambda c: c.time)

    candles_to_append_or_store = parsed_api_candles
    if latest_known_timestamp_in_db is not None:
        # Filter out candles that are older than or equal to the latest known timestamp in DB
        # and also ensure we are not appending duplicates by timestamp if any slip through.
        # A set of existing timestamps could be used if the API might return overlapping ranges
        # but for appending strictly newer data, this filter should suffice.
        original_api_count = len(parsed_api_candles)
        candles_to_append_or_store = [
            c for c in parsed_api_candles if c.time > latest_known_timestamp_in_db
        ]
        logger.info(f"Filtered API candles for {base_addr_lower}/{quote_addr_lower}: {len(candles_to_append_or_store)} new candles out of {original_api_count} (latest_known_timestamp_in_db: {latest_known_timestamp_in_db}).")


    if not candles_to_append_or_store and ohlcv_candles_data: # If API data was provided but all were old/filtered
        logger.info(f"No new candles to append for {base_addr_lower}/{quote_addr_lower} after filtering. Original API count: {len(ohlcv_candles_data)}. Will update last_updated if document exists.")
        # We still want to update 'last_updated' to signify we checked.
    elif not ohlcv_candles_data: # No API data provided at all
        logger.info(f"No API candle data provided for {base_addr_lower}/{quote_addr_lower}. Nothing to store or append.")
        return

    query_filter = {
        "chain_id": chain_id,
        "base_token_address": base_addr_lower,
        "quote_token_address": quote_addr_lower,
        "period_seconds": period_seconds,
        "timeframe": timeframe
    }

    try:
        existing_doc = await collection.find_one(query_filter, {"_id": 1, "ohlcv_candles": {"$slice": 1}}) # Check existence efficiently

        if existing_doc:
            if candles_to_append_or_store:
                # Document exists, and we have new candles to append
                update_operation = {
                    "$push": {"ohlcv_candles": {"$each": [c.model_dump() for c in candles_to_append_or_store]}},
                    "$set": {
                        "last_updated": datetime.now(timezone.utc),
                        "base_token_symbol": base_token_symbol,
                        "quote_token_symbol": quote_token_symbol,
                        "chain_name": chain_name
                    }
                }
                result = await collection.update_one(query_filter, update_operation)
                if result.modified_count > 0:
                    logger.info(f"Appended {len(candles_to_append_or_store)} new OHLCV candles to DB for {base_addr_lower}/{quote_addr_lower} on chain {chain_id} ({timeframe}).")
                elif result.matched_count > 0:
                    logger.info(f"Matched existing OHLCV data for {base_addr_lower}/{quote_addr_lower} but no modification made (possibly due to identical $set or empty $push). Appended count: {len(candles_to_append_or_store)}.")
                else:
                    logger.warning(f"Attempted to append candles for {base_addr_lower}/{quote_addr_lower} but no document matched the filter. This shouldn't happen if existing_doc was found.")

            else:
                # Document exists, but no new candles to append (all API candles were old or filtered out)
                # Still update last_updated and other identifiers to show we checked
                update_set_fields = {
                    "last_updated": datetime.now(timezone.utc),
                    "base_token_symbol": base_token_symbol,
                    "quote_token_symbol": quote_token_symbol,
                    "chain_name": chain_name
                }
                result = await collection.update_one(query_filter, {"$set": update_set_fields})
                if result.modified_count > 0:
                    logger.info(f"Updated metadata (last_updated, symbols, chain_name) for existing OHLCV data for {base_addr_lower}/{quote_addr_lower} (no new candles to append).")
                else:
                    logger.info(f"No new candles to append and metadata was not modified for {base_addr_lower}/{quote_addr_lower} (already recent or no match).")

        else: # Document does not exist, insert new
            if not candles_to_append_or_store:
                 logger.warning(f"No document found and no valid candles to store for new entry {base_addr_lower}/{quote_addr_lower}. Original API data count: {len(ohlcv_candles_data)}")
                 return # Avoid creating an empty document if all initial candles were filtered out (unlikely for a new entry)
            
            logger.info(f"Creating new OHLCV document for {base_addr_lower}/{quote_addr_lower} with {len(candles_to_append_or_store)} candles.")
            document_to_store = StoredOHLCVData(
                chain_id=chain_id,
                base_token_address=base_addr_lower,
                quote_token_address=quote_addr_lower,
                period_seconds=period_seconds,
                timeframe=timeframe,
                base_token_symbol=base_token_symbol,
                quote_token_symbol=quote_token_symbol,
                chain_name=chain_name,
                ohlcv_candles=candles_to_append_or_store,
                last_updated=datetime.now(timezone.utc)
            )
            update_data = {"$set": document_to_store.model_dump(by_alias=True)}
            result = await collection.update_one(query_filter, update_data, upsert=True)

            if result.upserted_id:
                logger.info(f"Inserted new OHLCV data into DB (async) for {base_addr_lower}/{quote_addr_lower} on chain {chain_id} ({timeframe}). ID: {result.upserted_id} with {len(candles_to_append_or_store)} candles.")
            elif result.modified_count > 0: # Should not happen with upsert=True on a non-existing doc unless race condition
                logger.info(f"Updated (unexpectedly, should have been upsert) OHLCV data for {base_addr_lower}/{quote_addr_lower}.")
            else:
                logger.warning(f"OHLCV data for {base_addr_lower}/{quote_addr_lower} was not inserted via upsert. Matched: {result.matched_count}")
                
    except OperationFailure as e:
        logger.error(f"MongoDB async operation failure during store_ohlcv_in_db: {e}")
        if hasattr(e, 'code') and e.code == 11000: 
            logger.error(f"Duplicate key error (async) during store_ohlcv_in_db for {base_addr_lower}/{quote_addr_lower}. Query: {query_filter}. Details: {e.details if hasattr(e, 'details') else 'N/A'}")
    except Exception as e:
        logger.error(f"Unexpected error during async store_ohlcv_in_db for {base_addr_lower}/{quote_addr_lower}: {e}", exc_info=True)

async def get_portfolio_from_cache(
    chain_id: int,
    timeframe: str,
    mvo_objective: str,
    risk_free_rate: float,
    annualization_factor: int
) -> Optional[Dict[str, Any]]:
    """
    Retrieves cached portfolio optimization results from MongoDB.
    """
    global db
    if db is None:
        logger.error("Async database connection not available for get_portfolio_from_cache.")
        return None

    collection: AsyncIOMotorCollection = db[PORTFOLIO_COLLECTION_NAME]
    query = {
        "chain_id": chain_id,
        "timeframe": timeframe,
        "mvo_objective": mvo_objective,
        "risk_free_rate": risk_free_rate,
        "annualization_factor": annualization_factor
    }
    
    logger.debug(f"Querying portfolio cache with: {query}")
    
    try:
        document = await collection.find_one(query)
        if document:
            logger.debug(f"Found portfolio document in cache: {document.get('_id', 'no_id')} with last_updated: {document.get('last_updated', 'no_timestamp')}")
            stored_portfolio = StoredPortfolioData(**document)
            
            cache_duration = timedelta(seconds=CACHE_DURATION_PORTFOLIO_SECONDS)
            last_updated_aware = stored_portfolio.last_updated
            if last_updated_aware.tzinfo is None:
                last_updated_aware = last_updated_aware.replace(tzinfo=timezone.utc)

            if datetime.now(timezone.utc) - last_updated_aware < cache_duration:
                logger.info(f"Found fresh portfolio data in cache for chain {chain_id} ({timeframe}, {mvo_objective}).")
                
                # Convert back to the expected format
                portfolio_weights_dict = {pw.asset_symbol: pw.weight for pw in stored_portfolio.portfolio_weights}
                
                return {
                    "optimized_portfolio": {
                        "weights": portfolio_weights_dict,
                        "expected_annual_return": stored_portfolio.expected_annual_return,
                        "annual_volatility": stored_portfolio.annual_volatility,
                        "sharpe_ratio": stored_portfolio.sharpe_ratio,
                        "assets_with_allocation": len(stored_portfolio.portfolio_weights),
                        "total_assets_considered": stored_portfolio.total_assets_screened
                    },
                    "selected_for_portfolio": stored_portfolio.selected_assets,
                    "total_assets_considered": stored_portfolio.total_assets_screened,
                    "data_source": "cache"
                }
            else:
                logger.info(f"Found stale portfolio data in cache for chain {chain_id} ({timeframe}). Will re-calculate.")
                return None
        else:
            logger.info(f"No portfolio data found in cache for chain {chain_id} ({timeframe}, {mvo_objective}).")
            return None
    except Exception as e:
        logger.error(f"Unexpected error during get_portfolio_from_cache: {e}", exc_info=True)
        return None

async def store_portfolio_in_cache(
    chain_id: int,
    timeframe: str,
    mvo_objective: str,
    risk_free_rate: float,
    annualization_factor: int,
    portfolio_result: Dict[str, Any]
):
    """
    Stores portfolio optimization results in MongoDB cache.
    """
    global db
    if db is None:
        logger.error("Async database connection not available for store_portfolio_in_cache.")
        return

    collection: AsyncIOMotorCollection = db[PORTFOLIO_COLLECTION_NAME]
    
    try:
        # Extract data from portfolio_result
        optimized_portfolio = portfolio_result.get("optimized_portfolio", {})
        weights_dict = optimized_portfolio.get("weights", {})
        selected_assets = portfolio_result.get("selected_for_portfolio", [])
        total_considered = portfolio_result.get("total_assets_considered", 0)
        
        # Convert weights dict to list of PortfolioWeights
        portfolio_weights = [
            PortfolioWeights(asset_symbol=symbol, weight=weight)
            for symbol, weight in weights_dict.items()
        ]
        
        document_to_store = StoredPortfolioData(
            chain_id=chain_id,
            timeframe=timeframe,
            num_top_assets=len(selected_assets),  # Store actual number of assets with allocation
            mvo_objective=mvo_objective,
            risk_free_rate=risk_free_rate,
            annualization_factor=annualization_factor,
            portfolio_weights=portfolio_weights,
            expected_annual_return=optimized_portfolio.get("expected_annual_return", 0.0),
            annual_volatility=optimized_portfolio.get("annual_volatility", 0.0),
            sharpe_ratio=optimized_portfolio.get("sharpe_ratio", 0.0),
            selected_assets=selected_assets,
            total_assets_screened=total_considered,
            last_updated=datetime.now(timezone.utc)
        )
        
        query_filter = {
            "chain_id": chain_id,
            "timeframe": timeframe,
            "mvo_objective": mvo_objective,
            "risk_free_rate": risk_free_rate,
            "annualization_factor": annualization_factor
        }
        
        update_data = {"$set": document_to_store.model_dump(by_alias=True)}

        result = await collection.update_one(query_filter, update_data, upsert=True)
        if result.upserted_id:
            logger.info(f"Inserted new portfolio data into cache for chain {chain_id} ({timeframe}, {len(selected_assets)} assets with allocation). ID: {result.upserted_id}")
        elif result.modified_count > 0:
            logger.info(f"Updated existing portfolio data in cache for chain {chain_id} ({timeframe}, {len(selected_assets)} assets with allocation).")
        elif result.matched_count > 0 and result.modified_count == 0:
            logger.info(f"Portfolio data for chain {chain_id} ({timeframe}) matched but was identical, no update needed.")
        else:
            logger.warning(f"Portfolio data for chain {chain_id} ({timeframe}) was not inserted or modified. Matched: {result.matched_count}")

    except Exception as e:
        logger.error(f"Unexpected error during store_portfolio_in_cache: {e}", exc_info=True)

async def store_forecast_signals(
    signals_to_store: List[ForecastSignalRecord]
):
    """
    Stores a list of forecast signals in the forecast_signals collection.
    Uses bulk insert for efficiency.
    """
    global db
    if db is None:
        logger.error("Async database connection not available for store_forecast_signals.")
        return
    if not signals_to_store:
        logger.info("No forecast signals provided to store.")
        return

    collection: AsyncIOMotorCollection = db[FORECAST_SIGNALS_COLLECTION_NAME]
    operations = []
    for signal_record in signals_to_store:
        # We will simply insert. If you need update logic, it's more complex.
        # For simplicity, this will insert new documents for each signal generation event.
        # Querying for the "latest" signal of a type for an asset would be done by sorting by forecast_timestamp.
        operations.append(pymongo.InsertOne(signal_record.model_dump(by_alias=True)))
    
    try:
        if operations:
            result = await collection.bulk_write(operations, ordered=False)
            logger.info(f"Stored {result.inserted_count} forecast signals in DB. Matched: {result.matched_count}, Modified: {result.modified_count}, Upserted: {result.upserted_count}")
        else:
            logger.info("No valid forecast signal operations to perform.")
    except pymongo.errors.BulkWriteError as bwe:
        logger.error(f"Bulk write error during store_forecast_signals: {bwe.details}")
    except Exception as e:
        logger.error(f"Unexpected error during store_forecast_signals: {e}", exc_info=True)

async def get_recent_forecast_signals(
    asset_symbol_global: str,
    chain_id: int, # Original chain_id of the asset for an exact match
    timeframe: str, # Added timeframe parameter
    max_forecast_age_hours: int = 4 # e.g., forecasts older than 4 hours are stale
) -> Optional[List[ForecastSignalRecord]]:
    """
    Retrieves recent forecast signals for a specific asset from the forecast_signals collection.
    """
    global db
    if db is None:
        logger.error("Async database connection not available for get_recent_forecast_signals.")
        return None

    collection: AsyncIOMotorCollection = db[FORECAST_SIGNALS_COLLECTION_NAME]
    
    # Calculate the earliest acceptable forecast timestamp
    earliest_acceptable_time = datetime.now(timezone.utc) - timedelta(hours=max_forecast_age_hours)
    earliest_acceptable_timestamp_sec = int(earliest_acceptable_time.timestamp())

    query = {
        "asset_symbol": asset_symbol_global,
        "chain_id": chain_id, # Ensure we match the asset on its original chain
        "timeframe": timeframe, # Added timeframe to query
        "forecast_timestamp": {"$gte": earliest_acceptable_timestamp_sec}
    }
    
    logger.debug(f"Querying recent forecast signals with: {query}")
    
    signals_cursor = collection.find(query).sort("forecast_timestamp", pymongo.DESCENDING)
    
    all_recent_signals_for_asset = []
    async for doc in signals_cursor:
        # Handle potential old field name 'token_address'
        if "token_address" in doc and "base_token_address" not in doc:
            doc["base_token_address"] = doc.pop("token_address")
        
        # Ensure other new optional fields are at least present as None if missing,
        # though Pydantic's Optional with default None handles this.
        # This is more for explicit clarity if needed or if defaults weren't set in model.
        # if "quote_token_address" not in doc:
        #     doc["quote_token_address"] = None
        # if "base_token_symbol" not in doc:
        #     doc["base_token_symbol"] = None
        # if "quote_token_symbol" not in doc:
        #     doc["quote_token_symbol"] = None

        try:
            all_recent_signals_for_asset.append(ForecastSignalRecord(**doc))
        except Exception as e:
            logger.error(f"Failed to parse document into ForecastSignalRecord for asset {asset_symbol_global}, doc_id {doc.get('_id')}: {e}. Document: {doc}")
            continue # Skip this problematic document
    
    if not all_recent_signals_for_asset:
        logger.info(f"No recent forecast signals found in DB for {asset_symbol_global} (chain {chain_id}) within last {max_forecast_age_hours} hours.")
        return None

    # Find the latest forecast_timestamp among the retrieved signals
    latest_forecast_batch_timestamp = 0
    if all_recent_signals_for_asset:
        latest_forecast_batch_timestamp = max(s.forecast_timestamp for s in all_recent_signals_for_asset)
    
    # Filter to include only signals from that very latest batch
    signals_from_latest_batch = [
        s for s in all_recent_signals_for_asset if s.forecast_timestamp == latest_forecast_batch_timestamp
    ]

    if signals_from_latest_batch:
        logger.info(f"Found {len(signals_from_latest_batch)} recent signals from batch @ {latest_forecast_batch_timestamp} for {asset_symbol_global} (chain {chain_id}).")
        return signals_from_latest_batch
    else:
        # This case should be rare if all_recent_signals_for_asset was populated
        logger.info(f"No signals found matching the latest batch timestamp for {asset_symbol_global}, though recent signals were present.")
        return None

async def close_mongo_connection():
    """Closes the MongoDB connection asynchronously if it's open."""
    global mongo_client, db
    if mongo_client:
        logger.info("Closing MongoDB connection (async).")
        mongo_client.close() # motor client close is synchronous
        mongo_client = None
    # Ensure db is also None if client is None / closed
    db = None

async def get_mvo_data_from_db(
    asset_identifiers: List[Dict[str, Any]],
    expected_return_signal_type: Optional[str] = None,  # Make optional
    ohlcv_history_points: int = 100,
    fallback_er_if_signal_missing: float = 0.0,
    fetch_expected_returns: bool = True  # Add flag to skip ER fetching
) -> Tuple[Optional[pd_Series], Optional[Dict[str, pd_DataFrame]]]:
    """
    Fetches expected returns from forecast signals and/or historical close prices for MVO.
    """
    global db
    if db is None:
        logger.error("Async database connection not available for get_mvo_data_from_db.")
        return None, None

    expected_returns_data = {}
    historical_closes_data = {}

    # --- 1. Fetch Expected Returns from Forecast Signals (if requested) ---
    if fetch_expected_returns and expected_return_signal_type:
        asset_symbols_query_list = list(set(aid["asset_symbol_global"] for aid in asset_identifiers))
        chain_ids_query_list = list(set(aid["chain_id"] for aid in asset_identifiers))

        if asset_symbols_query_list and chain_ids_query_list:
            pipeline = [
                {
                    "$match": {
                        "asset_symbol": {"$in": asset_symbols_query_list},
                        "chain_id": {"$in": chain_ids_query_list},
                        "signal_type": expected_return_signal_type
                    }
                },
                {"$sort": {"asset_symbol": 1, "chain_id": 1, "forecast_timestamp": -1}},
                {
                    "$group": {
                        "_id": {"asset_symbol": "$asset_symbol"},
                        "latest_signal_doc": {"$first": "$$ROOT"}
                    }
                },
                {"$replaceRoot": {"newRoot": "$latest_signal_doc"}}
            ]
            try:
                forecast_signals_collection: AsyncIOMotorCollection = db[FORECAST_SIGNALS_COLLECTION_NAME]
                cursor = forecast_signals_collection.aggregate(pipeline)
                async for signal_doc in cursor:
                    asset_symbol = signal_doc.get("asset_symbol")
                    er_value = signal_doc.get("confidence") 
                    if asset_symbol and er_value is not None:
                        expected_returns_data[asset_symbol] = float(er_value)
                logger.info(f"Fetched expected returns for {len(expected_returns_data)} assets using signal type '{expected_return_signal_type}'.")
            except Exception as e:
                logger.error(f"Error fetching expected returns from signals: {e}", exc_info=True)

    # --- 2. Fetch Historical Close Prices for Covariance ---
    ohlcv_collection: AsyncIOMotorCollection = db[OHLCV_COLLECTION_NAME]
    
    # Batch fetch for better performance
    batch_size = 50
    for i in range(0, len(asset_identifiers), batch_size):
        batch = asset_identifiers[i:i+batch_size]
        
        # Build OR query for batch
        or_conditions = []
        for asset_info in batch:
            or_conditions.append({
                "chain_id": asset_info["chain_id"],
                "base_token_address": asset_info["base_token_address"].lower(),
                "quote_token_address": asset_info["quote_token_address"].lower(),
                "period_seconds": asset_info["period_seconds"],
                "timeframe": asset_info["timeframe"]
            })
        
        if or_conditions:
            query = {"$or": or_conditions}
            projection = {"ohlcv_candles": {"$slice": -ohlcv_history_points}, "_id": 0, 
                         "base_token_address": 1, "quote_token_address": 1, "chain_id": 1}
            
            try:
                cursor = ohlcv_collection.find(query, projection)
                async for doc in cursor:
                    # Find the matching asset identifier
                    for asset_info in batch:
                        if (doc.get("chain_id") == asset_info["chain_id"] and
                            doc.get("base_token_address", "").lower() == asset_info["base_token_address"].lower() and
                            doc.get("quote_token_address", "").lower() == asset_info["quote_token_address"].lower()):
                            
                            asset_symbol = asset_info["asset_symbol_global"]
                            if "ohlcv_candles" in doc and doc["ohlcv_candles"]:
                                candles_df_data = [
                                    {"timestamp": c.get("time"), "close": c.get("close")} 
                                    for c in doc["ohlcv_candles"] 
                                    if c.get("time") is not None and c.get("close") is not None
                                ]
                                if candles_df_data:
                                    df = pd_DataFrame(candles_df_data)
                                    df.sort_values(by="timestamp", inplace=True, ignore_index=True)
                                    df['close'] = pd.to_numeric(df['close'], errors='coerce')
                                    df.dropna(subset=['close'], inplace=True)
                                    if not df.empty:
                                        historical_closes_data[asset_symbol] = df[['timestamp', 'close']]
                            break
            except Exception as e:
                logger.error(f"Error batch fetching historical closes: {e}", exc_info=True)

    # Only create expected returns series if we fetched them
    if fetch_expected_returns:
        # Fill missing expected returns with fallback
        for aid in asset_identifiers:
            symbol = aid["asset_symbol_global"]
            if symbol not in expected_returns_data:
                logger.warning(f"No expected return found for {symbol}. Using fallback: {fallback_er_if_signal_missing}")
                expected_returns_data[symbol] = fallback_er_if_signal_missing
                
        final_expected_returns_series = pd_Series(expected_returns_data, name="expected_returns") if expected_returns_data else pd_Series(dtype=float, name="expected_returns")
    else:
        final_expected_returns_series = pd_Series(dtype=float, name="expected_returns")

    logger.info(f"Fetched historical closes for {len(historical_closes_data)} assets with history points: {ohlcv_history_points}.")
    
    return final_expected_returns_series, historical_closes_data

async def get_cross_chain_portfolio_from_cache(
    chain_ids_str: str,
    timeframe: str,
    max_tokens_per_chain: int,
    mvo_objective: str,
    risk_free_rate: float,
    annualization_factor_override: Optional[int],
    target_return: Optional[float]
) -> Optional[Dict[str, Any]]: # Returns the CrossChainPortfolioResponse dict
    global db
    if db is None:
        logger.error("Async database connection not available for get_cross_chain_portfolio_from_cache.")
        return None

    collection: AsyncIOMotorCollection = db[CROSS_CHAIN_PORTFOLIO_COLLECTION_NAME]
    query = {
        "request_chain_ids_str": chain_ids_str,
        "request_timeframe": timeframe,
        "request_max_tokens_per_chain": max_tokens_per_chain,
        "request_mvo_objective": mvo_objective,
        "request_risk_free_rate": risk_free_rate,
        "request_annualization_factor_override": annualization_factor_override,
        "request_target_return": target_return
    }
    
    logger.debug(f"Querying cross-chain portfolio cache with: {query}")
    
    try:
        document = await collection.find_one(query)
        if document:
            logger.debug(f"Found cross-chain portfolio document in cache: {document.get('_id', 'no_id')} with last_updated: {document.get('last_updated', 'no_timestamp')}")
            
            # Use StoredCrossChainPortfolioData to parse the document from DB
            # This also helps validate the structure before using it.
            stored_data = StoredCrossChainPortfolioData(**document)
            
            cache_duration = timedelta(seconds=CACHE_DURATION_CROSS_CHAIN_SECONDS)
            last_updated_aware = stored_data.last_updated
            if last_updated_aware.tzinfo is None:
                last_updated_aware = last_updated_aware.replace(tzinfo=timezone.utc)

            if datetime.now(timezone.utc) - last_updated_aware < cache_duration:
                logger.info(f"Found FRESH cross-chain portfolio data in cache for request: {chain_ids_str}, {timeframe}, {mvo_objective}. Last updated: {last_updated_aware}")
                # Return the nested response_data directly, which should be a CrossChainPortfolioResponse model (or its dict form)
                return stored_data.response_data.model_dump() # Return as dict for FastAPI
            else:
                logger.info(f"Found STALE cross-chain portfolio data in cache for request: {chain_ids_str}, {timeframe}. Will re-calculate.")
                return None # Stale data
        else:
            logger.info(f"No cross-chain portfolio data found in cache for request: {chain_ids_str}, {timeframe}, {mvo_objective}.")
            return None # No data at all
    except Exception as e:
        logger.error(f"Unexpected error during get_cross_chain_portfolio_from_cache: {e}", exc_info=True)
        return None

async def store_cross_chain_portfolio_in_cache(
    chain_ids_str: str,
    timeframe: str,
    max_tokens_per_chain: int,
    mvo_objective: str,
    risk_free_rate: float,
    annualization_factor_override: Optional[int],
    target_return: Optional[float],
    portfolio_response_data: Dict[str, Any] # This should be the dict form of CrossChainPortfolioResponse
):
    global db
    if db is None:
        logger.error("Async database connection not available for store_cross_chain_portfolio_in_cache.")
        return

    collection: AsyncIOMotorCollection = db[CROSS_CHAIN_PORTFOLIO_COLLECTION_NAME]
    
    try:
        # Create the Pydantic model for storage
        # The portfolio_response_data is already a dict, CrossChainPortfolioResponse.model_validate should handle it
        from models import CrossChainPortfolioResponse as CrossChainPortfolioResponseModel # Local import for clarity
        
        # Validate and structure the response_data part first
        validated_response = CrossChainPortfolioResponseModel(**portfolio_response_data)

        document_to_store = StoredCrossChainPortfolioData(
            request_chain_ids_str=chain_ids_str,
            request_timeframe=timeframe,
            request_max_tokens_per_chain=max_tokens_per_chain,
            request_mvo_objective=mvo_objective,
            request_risk_free_rate=risk_free_rate,
            request_annualization_factor_override=annualization_factor_override,
            request_target_return=target_return,
            response_data=validated_response, # Store the validated Pydantic model
            last_updated=datetime.now(timezone.utc)
        )
        
        query_filter = {
            "request_chain_ids_str": chain_ids_str,
            "request_timeframe": timeframe,
            "request_max_tokens_per_chain": max_tokens_per_chain,
            "request_mvo_objective": mvo_objective,
            "request_risk_free_rate": risk_free_rate,
            "request_annualization_factor_override": annualization_factor_override,
            "request_target_return": target_return
        }
        
        update_data = {"$set": document_to_store.model_dump(by_alias=True)}

        result = await collection.update_one(query_filter, update_data, upsert=True)
        if result.upserted_id:
            logger.info(f"Inserted new cross-chain portfolio data into cache. Request: {chain_ids_str}, {timeframe}. ID: {result.upserted_id}")
        elif result.modified_count > 0:
            logger.info(f"Updated existing cross-chain portfolio data in cache. Request: {chain_ids_str}, {timeframe}.")
        elif result.matched_count > 0 and result.modified_count == 0:
            logger.info(f"Cross-chain portfolio data for request {chain_ids_str}, {timeframe} matched but was identical, no update needed.")
        else:
            logger.warning(f"Cross-chain portfolio data for request {chain_ids_str}, {timeframe} was not inserted or modified. Matched: {result.matched_count}")

    except Exception as e:
        logger.error(f"Unexpected error during store_cross_chain_portfolio_in_cache for request {chain_ids_str}, {timeframe}: {e}", exc_info=True)