    # ====================== Process Tokens ======================
    def process_tokens(self, tokens):
        new_tokens_count = 0
        posted_tokens_count = 0

        for pool in tokens:
            try:
                contract = pool.get("coinType")
                if not contract:
                    continue
                contract = contract.lower()

                # Skip already posted tokens
                if self.is_token_posted(contract):
                    logging.debug(f"Already posted: {contract}")
                    continue

                # Extract token info safely
                coin_metadata = pool.get("coinMetadata") or {}
                name = (
                    coin_metadata.get("name")
                    or coin_metadata.get("symbol")
                    or pool.get("name")
                    or pool.get("symbol")
                    or "Unknown Token"
                ).strip()

                if name == "Unknown Token":
                    logging.warning(f"Skipping unknown token: {contract}")
                    continue

                pool_id = pool.get("coinType")

                # Extract socials
                creator_data = pool.get("creatorData") or {}
                twitter = creator_data.get("twitterHandle")
                telegram = creator_data.get("telegramHandle")
                socials = {}
                if twitter:
                    socials["twitter"] = f"https://x.com/{twitter.lstrip('@').strip()}"
                if telegram:
                    socials["telegram"] = telegram

                # Other info
                token_image = coin_metadata.get("icon_url") or coin_metadata.get("iconUrl")
                creator_address = pool.get("creatorAddress")
                market_data = pool.get("marketData") or {}
                market_cap = market_data.get("marketCap")
                is_protected = pool.get("isProtected", False)

                # Dev Initial Buy
                creator_balance = pool.get("creatorBalance")
                creator_percent = pool.get("creatorPercent")
                dev_buy_text = None
                if creator_balance:
                    if creator_percent:
                        dev_buy_text = f"Dev Initial: {creator_balance:,} tokens ({creator_percent}%)"
                    else:
                        dev_buy_text = f"Dev Initial: {creator_balance:,} tokens"

                logging.warning(
                    f"📢 Preparing to post token: {name} ({contract}) | "
                    f"MarketCap: {market_cap} | Protected: {is_protected} | "
                    f"Dev: {dev_buy_text or 'N/A'} | X: {twitter or 'N/A'} | TG: {telegram or 'N/A'}"
                )

                # Build Telegram message
                message = telegram_bot.format_token_message(
                    token_name=name,
                    symbol=coin_metadata.get("symbol", ""),
                    contract_address=contract,
                    coinType=pool_id,
                    creator_address=creator_address,
                    socials=socials if socials else None,
                    market_cap=market_cap,
                    is_protected=is_protected,
                    dev_initial_buy=dev_buy_text,
                )

                # Create buy button safely
                buy_button = telegram_bot.create_buy_button(pool_id) if pool_id else None

                # Post to Telegram
                if token_image and token_image.startswith("data:image"):
                    telegram_result = telegram_bot.send_photo(token_image, message, buy_button)
                else:
                    telegram_result = telegram_bot.send_message(message, buy_button)

                if
