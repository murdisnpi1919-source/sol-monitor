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

# =================

def send(msg):
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={
            "chat_id": CHAT_ID,
            "message_thread_id": THREAD_ID,
            "text": msg,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
    )

def rpc(payload):
    r = requests.post(RPC_URL, json=payload)
    return r.json().get("result")

# 🔥 limit=50 に変更済み
def get_signatures(addr):
    return rpc({
        "jsonrpc":"2.0","id":1,
        "method":"getSignaturesForAddress",
        "params":[addr, {"limit":50}]
    }) or []

def get_tx(sig):
    return rpc({
        "jsonrpc":"2.0","id":1,
        "method":"getTransaction",
        "params":[sig, {"encoding":"jsonParsed"}]
    })

def get_balance(addr):
    result = rpc({
        "jsonrpc":"2.0","id":1,
        "method":"getBalance",
        "params":[addr]
    })
    return result["value"] / 1_000_000_000

def get_token_info(mint):
    try:
        url = f"https://api.dexscreener.com/latest/dex/tokens/{mint}"
        r = requests.get(url, timeout=10)
        data = r.json()

        pairs = data.get("pairs")
        if not pairs:
            return "Unknown", "N/A", "N/A"

        pair = pairs[0]
        base = pair.get("baseToken", {})
        token_name = base.get("symbol") or base.get("name") or "Unknown"

        fdv = pair.get("fdv")
        mc_text = f"${int(fdv):,}" if fdv else "N/A"

        created_at = pair.get("pairCreatedAt")
        if created_at:
            seconds = int(time.time()) - int(created_at / 1000)
            hours = seconds // 3600
            age_text = f"{hours}h" if hours < 24 else f"{hours//24}d"
        else:
            age_text = "N/A"

        return token_name, mc_text, age_text

    except:
        return "Unknown", "N/A", "N/A"

# =================

def run():
    global last_balances

    for wallet in TARGET_WALLETS:

        wallet_link = f"<a href='https://solscan.io/account/{wallet}'>{wallet}</a>"

        # ① 残高減少検知
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

        # ② 送金チェック
        sigs = get_signatures(wallet)

        for s in reversed(sigs):  # 古い順に処理
            sig = s["signature"]
            if sig in seen:
                continue
            seen.add(sig)

            tx = get_tx(sig)
            if not tx:
                continue

            meta = tx.get("meta")

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

    # ③ 新規ウォレット購入検知
    for wallet in list(tracked_new_wallets.keys()):

        wallet_link = f"<a href='https://solscan.io/account/{wallet}'>{wallet}</a>"
        sigs = get_signatures(wallet)

        for s in reversed(sigs):
            sig = s["signature"]
            tx = get_tx(sig)
            if not tx:
                continue

            meta = tx.get("meta")
            if not meta:
                continue

            post_tokens = meta.get("postTokenBalances")
            pre_tokens = meta.get("preTokenBalances")

            if not post_tokens:
                continue

            for post_tb in post_tokens:
                if post_tb.get("owner") != wallet:
                    continue

                mint = post_tb.get("mint")
                post_amount = int(post_tb.get("uiTokenAmount", {}).get("amount", 0))

                pre_amount = 0
                if pre_tokens:
                    for pre_tb in pre_tokens:
                        if pre_tb.get("mint") == mint and pre_tb.get("owner") == wallet:
                            pre_amount = int(pre_tb.get("uiTokenAmount", {}).get("amount", 0))
                            break

                if post_amount > pre_amount:
                    token_name, mc, age = get_token_info(mint)

                    send(
                        f"🚀 <b>新規ウォレット購入検知</b>\n\n"
                        f"👛 {wallet_link}\n\n"
                        f"🪙 <b>{token_name}</b>\n"
                        f"📊 MC: {mc}\n"
                        f"🗓 Age: {age}\n\n"
                        f"🔗 https://solscan.io/tx/{sig}"
                    )

                    del tracked_new_wallets[wallet]
                    break
            else:
                continue
            break
