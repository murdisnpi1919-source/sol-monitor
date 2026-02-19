import requests
import time
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

THREAD_PRIORITY = 5197
THREAD_WIDE = 5238

BINGX_ADDRESS = "J1BDJEdvTmmcjeTMVTHLPaaNvuQ3mdxeuWEM1YyMksLy"
RPC_URL = "https://api.mainnet-beta.solana.com"

tracked_wallets = {}
seen = set()


def send(msg, thread_id):
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={
            "chat_id": CHAT_ID,
            "message_thread_id": thread_id,
            "text": msg,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
    )


def rpc(payload):
    r = requests.post(RPC_URL, json=payload, timeout=15)
    return r.json().get("result")


def get_signatures(addr):
    return rpc({
        "jsonrpc": "2.0", "id": 1,
        "method": "getSignaturesForAddress",
        "params": [addr, {"limit": 50}]
    }) or []


def get_tx(sig):
    return rpc({
        "jsonrpc": "2.0", "id": 1,
        "method": "getTransaction",
        "params": [sig, {"encoding": "jsonParsed"}]
    })


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


def run():
    sigs = get_signatures(BINGX_ADDRESS)

    for s in sigs:
        sig = s["signature"]
        if sig in seen:
            continue
        seen.add(sig)

        tx = get_tx(sig)
        if not tx:
            continue

        for ix in tx["transaction"]["message"]["instructions"]:
            if ix.get("program") != "system":
                continue

            info = ix.get("parsed", {}).get("info", {})
            source = info.get("source")
            destination = info.get("destination")
            lamports = info.get("lamports")

            if source != BINGX_ADDRESS or not lamports:
                continue

            sol = lamports / 1_000_000_000
            wallet_link = f"<a href='https://solscan.io/account/{destination}'>{destination}</a>"

            if 11 <= sol <= 13.5:
                send(
                    f"🔴 <b>超重要レンジ検知</b>\n\n"
                    f"<b>💰 {sol:.4f} SOL</b>\n\n"
                    f"👛 {wallet_link}",
                    THREAD_PRIORITY
                )
                tracked_wallets[destination] = True

            elif 8 <= sol <= 16:
                send(
                    f"🎯 <b>8-16 SOL 出金検知</b>\n\n"
                    f"💰 {sol:.4f} SOL\n\n"
                    f"👛 {wallet_link}",
                    THREAD_PRIORITY
                )
                tracked_wallets[destination] = True

            elif 3 <= sol <= 30:
                send(
                    f"📡 <b>3-30 SOL 検知</b>\n\n"
                    f"💰 {sol:.4f} SOL\n\n"
                    f"👛 {wallet_link}",
                    THREAD_WIDE
                )

    # 初回購入追跡
    for wallet in list(tracked_wallets.keys()):
        sigs = get_signatures(wallet)

        for s in sigs[:5]:
            sig = s["signature"]
            tx = get_tx(sig)
            if not tx:
                continue

            meta = tx.get("meta")
            if not meta:
                continue

            pre = meta.get("preBalances")
            post = meta.get("postBalances")
            if not pre or not post:
                continue

            sol_spent = (pre[0] - post[0]) / 1_000_000_000
            if sol_spent <= 0:
                continue

            token_balances = meta.get("postTokenBalances")
            if not token_balances:
                continue

            mint = token_balances[0].get("mint")
            if not mint:
                continue

            token_name, mc, age = get_token_info(mint)
            wallet_link = f"<a href='https://solscan.io/account/{wallet}'>{wallet}</a>"

            send(
                f"🚀 <b>初回購入検知</b>\n\n"
                f"👛 {wallet_link}\n\n"
                f"🪙 <b>{token_name}</b>\n"
                f"💰 使用: {sol_spent:.4f} SOL\n\n"
                f"📊 MC: {mc}\n"
                f"🗓 Age: {age}\n\n"
                f"🔗 https://solscan.io/tx/{sig}",
                THREAD_PRIORITY
            )

            del tracked_wallets[wallet]

            break
