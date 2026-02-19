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
SEEN_LIMIT = 3000
last_balances = {}


# =================

def send(msg):
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={
                "chat_id": CHAT_ID,
                "message_thread_id": THREAD_ID,
                "text": msg,
                "parse_mode": "HTML",
                "disable_web_page_preview": True
            },
            timeout=15
        )
    except:
        pass


def rpc(payload):
    try:
        r = requests.post(RPC_URL, json=payload, timeout=15)
        return r.json().get("result")
    except:
        return None


def get_signatures(addr):
    return rpc({
        "jsonrpc": "2.0", "id": 1,
        "method": "getSignaturesForAddress",
        "params": [addr, {"limit": 100}]
    }) or []


def get_tx(sig):
    return rpc({
        "jsonrpc": "2.0", "id": 1,
        "method": "getTransaction",
        "params": [sig, {"encoding": "jsonParsed"}]
    })


def get_balance(addr):
    result = rpc({
        "jsonrpc": "2.0", "id": 1,
        "method": "getBalance",
        "params": [addr]
    })
    if not result:
        return 0
    return result["value"] / 1_000_000_000


# =================

def run():
    global seen

    for wallet in TARGET_WALLETS:

        wallet_link = f"<a href='https://solscan.io/account/{wallet}'>{wallet}</a>"

        # ===============================
        # 残高監視
        # ===============================
        current_balance = get_balance(wallet)

        if wallet not in last_balances:
            last_balances[wallet] = current_balance
        else:
            diff = last_balances[wallet] - current_balance
            if diff >= 1:
                send(
                    f"⚠️ <b>1 SOL以上減少検知</b>\n\n"
                    f"👛 {wallet_link}\n\n"
                    f"💰 減少: {diff:.4f} SOL"
                )
            last_balances[wallet] = current_balance

        # ===============================
        # 送金監視（安全処理）
        # ===============================
        sigs = get_signatures(wallet)

        for s in reversed(sigs):
            sig = s["signature"]

            if sig in seen:
                continue

            tx = get_tx(sig)
            if not tx:
                continue

            # 🔥 tx取得成功後に登録
            seen.add(sig)
            if len(seen) > SEEN_LIMIT:
                seen = set(list(seen)[-1500:])

            for ix in tx["transaction"]["message"]["instructions"]:
                if ix.get("program") != "system":
                    continue

                info = ix.get("parsed", {}).get("info", {})
                source = info.get("source")
                destination = info.get("destination")
                lamports = info.get("lamports")

                if source == wallet and lamports:
                    sol = lamports / 1_000_000_000

                    if destination == BINGX_ADDRESS and sol >= 1:
                        send(
                            f"📤 <b>CEXへの送金検知</b>\n\n"
                            f"👛 From\n{wallet_link}\n\n"
                            f"💰 {sol:.4f} SOL\n\n"
                            f"🔗 https://solscan.io/tx/{sig}"
                        )

                    elif sol >= 1 and destination not in KNOWN_WALLETS:

                        destination_link = f"<a href='https://solscan.io/account/{destination}'>{destination}</a>"

                        send(
                            f"🚨 <b>未知ウォレット送金検知</b>\n\n"
                            f"👛 From\n{wallet_link}\n\n"
                            f"➡️ To\n{destination_link}\n\n"
                            f"💰 {sol:.4f} SOL\n\n"
                            f"🔗 https://solscan.io/tx/{sig}"
                        )

                        tracked_new_wallets[destination] = True
