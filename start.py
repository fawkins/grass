# Menampilkan ASCII Art di terminal saat program dijalankan
ascii_art = """
.·:'''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''':·.
: :  __  __                                                                : :
: : /  |/  |                                                               : :
: : $$ |$$ |                                                               : :
: : $$ |$$ |                                                               : :
: : $$/ $$/                                                                : :
: :                                                                        : :
: :                                                                        : :
: :                                                                        : :
: :                                                                        : :
: :  ________  ______   __       __  __    __  ______  __    __   ______   : :
: : /        |/      \ /  |  _  /  |/  |  /  |/      |/  \  /  | /      \  : :
: : $$$$$$$$//$$$$$$  |$$ | / \ $$ |$$ | /$$/ $$$$$$/ $$  \ $$ |/$$$$$$  | : :
: : $$ |__   $$ |__$$ |$$ |/$  \$$ |$$ |/$$/    $$ |  $$$  \$$ |$$ \__$$/  : :
: : $$    |  $$    $$ |$$ /$$$  $$ |$$  $$<     $$ |  $$$$  $$ |$$      \  : :
: : $$$$$/   $$$$$$$$ |$$ $$/$$ $$ |$$$$$  \    $$ |  $$ $$ $$ | $$$$$$  | : :
: : $$ |     $$ |  $$ |$$$$/  $$$$ |$$ |$$  \  _$$ |_ $$ |$$$$ |/  \__$$ | : :
: : $$ |     $$ |  $$ |$$$/    $$$ |$$ | $$  |/ $$   |$$ | $$$ |$$    $$/  : :
: : $$/      $$/   $$/ $$/      $$/ $$/   $$/ $$$$$$/ $$/   $$/  $$$$$$/   : :
: :                                                                        : :
: :                                                                        : :
: :                                                                        : :
: :                                                              __  __    : :
: :                                                             /  |/  |   : :
: :                                                             $$ |$$ |   : :
: :                                                             $$ |$$ |   : :
: :                                                             $$/ $$/    : :
: :                                                                        : :
: :                                                                        : :
: :                                                                        : :
: :                                                                        : :
'·:........................................................................:·'
"""

# Print ASCII Art ke terminal
print(ascii_art)

# Project: WebSocket Proxy Connector
import asyncio
import random
import ssl
import json
import time
import uuid
import websockets
from loguru import logger
from websockets_proxy import Proxy, proxy_connect
from fake_useragent import UserAgent

# Inisialisasi user agent untuk mengambil user-agent acak
user_agent = UserAgent()

async def connect_to_websocket(proxy, user_id):
    device_id = str(uuid.uuid4())
    logger.info(f"Device ID generated: {device_id}")
    
    while True:
        try:
            await asyncio.sleep(random.uniform(0.1, 1.0))
            custom_headers = {"User-Agent": user_agent.random}
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            uri = "wss://proxy.wynd.network:4650/"
            proxy_instance = Proxy.from_url(proxy)
            
            async with proxy_connect(uri, proxy=proxy_instance, ssl=ssl_context, extra_headers=custom_headers) as websocket:
                asyncio.create_task(send_periodic_ping(websocket))

                while True:
                    response = await websocket.recv()
                    await handle_server_message(response, websocket, device_id, user_id, proxy)

        except Exception as e:
            logger.error(f"Connection error with proxy {proxy}: {e}")
            await handle_proxy_error(proxy)
            await asyncio.sleep(5)

async def send_periodic_ping(websocket):
    while True:
        ping_message = json.dumps({
            "id": str(uuid.uuid4()),
            "version": "1.0.0",
            "action": "PING",
            "data": {}
        })
        logger.debug(f"Sending ping: {ping_message}")
        await websocket.send(ping_message)
        await asyncio.sleep(20)

async def handle_server_message(response, websocket, device_id, user_id, proxy):
    message = json.loads(response)
    logger.info(f"Received message: {message}")

    if message.get("action") == "AUTH":
        await send_auth_response(websocket, message, device_id, user_id)
    elif message.get("action") == "PONG":
        await send_pong_response(websocket, message)
        await update_proxy_status(proxy)

async def send_auth_response(websocket, message, device_id, user_id):
    auth_response = {
        "id": message["id"],
        "origin_action": "AUTH",
        "result": {
            "browser_id": device_id,
            "user_id": user_id,
            "user_agent": user_agent.random,
            "timestamp": int(time.time()),
            "device_type": "extension",
            "version": "3.3.2"
        },
    }
    logger.debug(f"Sending auth response: {auth_response}")
    await websocket.send(json.dumps(auth_response))

async def send_pong_response(websocket, message):
    pong_response = {"id": message["id"], "origin_action": "PONG"}
    logger.debug(f"Sending pong response: {pong_response}")
    await websocket.send(json.dumps(pong_response))

async def update_proxy_status(proxy):
    with open("active_proxies.txt", "a") as file:
        file.write(proxy[len("socks5://"):].strip() + "\n")
    logger.info(f"Proxy list updated with: {proxy}")

async def handle_proxy_error(proxy):
    if "Empty connect reply" in str(proxy):
        await remove_proxy_from_file("user_proxy.txt", proxy[len("socks5://"):])

async def remove_proxy_from_file(file_path, proxy):
    logger.info(f"Removing proxy {proxy} from {file_path}")
    if proxy.startswith("socks5://"):
        proxy = proxy[len("socks5://"):]

    try:
        with open(file_path, "r") as file:
            proxies = file.readlines()

        with open(file_path, "w") as file:
            for p in proxies:
                if p.strip() != proxy:
                    file.write(p)
        logger.info(f"Successfully removed {proxy} from {file_path}")
    except Exception as e:
        logger.error(f"Error removing {proxy} from {file_path}: {e}")

async def main():
    with open("user_id.txt", "r") as file:
        user_id = file.read().strip()

    with open("user_proxy.txt", "r") as file:
        proxies = [
            f'socks5://{line.strip()}' if not line.startswith("socks5://") else line.strip()
            for line in file
        ]

    connection_tasks = [asyncio.create_task(connect_to_websocket(proxy, user_id)) for proxy in proxies]
    await asyncio.gather(*connection_tasks)

if __name__ == "__main__":
    asyncio.run(main())
