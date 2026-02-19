import requests
import time
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
THREAD_ID = 5272

RPC_URL = "https://api.mainnet-beta.solana.com"

BINGX_ADDRESS = "J1BDJEdvTmmcjeTMVTHLPaaNvuQ3mdxeuWEM1YyMksLy"

TARGET_WALLETS = {
    "5NgLzxgz5zQYAQsFoECbjXkWo1HtAxAtMTwkCEuv2Vs8",
    "AUYRhnB5hPG7BN37DZsjbLttirYhf54v7h4rdWSzsmyb",
    "FAxyGyNphSJq9bYn6QGwSi82QnGaFjZHDcCeNRxiVQE9",
    "6s8gDZzRnrD2amtsKoj6AgE7RnHKAUzg4GDX9EC5CPzA",
    "6xYeLEozBU9YLdsX3GKoZabGKhjPgyAxVVJ4ym7MqXCN",
    "c3moQ5ss149K3EMYs5qb8gHwHwEK9V26FnMcES1o621",
}

KNOWN_WALLETS = TARGET_WALLETS.union({BINGX_ADDRESS})

tracked_new_wallets = {}
seen = set()
last_balances = {}