import requests
import logging
import time
from telegram_bot import telegram_bot

API_URL = "https://steep-thunder-1d39.vapexmeli1.workers.dev/"

posted_tokens = set()


def fetch_pools():
    try:
        resp = requests.get(API_URL, timeout=20)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logging.error(f"Error fetching pools: {e}")
        return []


def process_pool(pool: dict):
    try:
        token_name = pool.get("tokenName")
        contract_address = pool.get("contractAddress")
        pool_id = pool.get("poolId")

        creator_data = pool.get("creatorData", {})

        twitter_handle = creator_data.get("twitterHandle")
        followers = creator_data.get("followers")
        trusted_followers = creator_data.get("trustedFollowers")

        creator_address = pool.get("creatorAddress")
        market_cap = pool.get("marketCap")
        is_protected = pool.get("isProtected", False)

        if not contract_address or contract_address in posted_tokens:
            return

        # Formatimi i mesazhit
        message = telegram_bot.format_token_message(
            token_name=token_name,
            contract_address=contract_address,
            twitter_handle=twitter_handle,
            creator_address=creator_address,
            market_cap=market_cap,
            is_protected=is_protected,
            followers=followers,
            trusted_followers=trusted_followers,
        )

        # Butoni "Buy"
        button = telegram_bot.create_buy_button(pool_id)

        # Dërgo mesazhin
        telegram_bot.send_message(message, reply_markup=button)

        posted_tokens.add(contract_address)
        logging.info(f"Posted new token: {token_name} ({contract_address})")

    except Exception as e:
        logging.error(f"Error processing pool: {e}")


def start_monitoring():
    logging.info("Starting monitoring service...")
    while True:
        pools = fetch_pools()
        if pools:
            for pool in pools:
                process_pool(pool)
        time.sleep(15)  # kontrollon çdo 15 sekonda
