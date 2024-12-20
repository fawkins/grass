import asyncio
import random
import ssl
import json
import time
import uuid
from loguru import logger
from fake_useragent import UserAgent
import aiohttp
from aiohttp_socks import SocksConnector  

ascii_art = r"""
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

print(ascii_art)

user_agent = UserAgent()

async def connect_to_websocket(proxy, user_id, semaphore):
    device_id = str(uuid.uuid4())
    logger.info(f"Device ID generated: {device_id} for proxy {proxy}")
    
    async with semaphore:
        while True:
            try:
                await asyncio.sleep(random.uniform(0.1, 1.0))
                custom_headers = {"User-Agent": user_agent.random}
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                
                uri = "wss://proxy.wynd.network:4650/"
                connector = SocksConnector.from_url(proxy)  # Menggunakan SocksConnector

                async with aiohttp.ClientSession(connector=connector) as session:
                    async with session.ws_connect(uri, ssl=ssl_context, headers=custom_headers, timeout=aiohttp.ClientTimeout(total=60)) as websocket:
                        asyncio.create_task(send_periodic_ping(websocket))
                        while True:
                            response = await websocket.receive()
                            if response.type == aiohttp.WSMsgType.TEXT:
                                await handle_server_message(response.data, websocket, device_id, user_id, proxy)
            except aiohttp.ClientError as e:
                logger.error(f"Client error with proxy {proxy}: {e}")
                await handle_proxy_error(proxy)
                await asyncio.sleep(5)
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
        await websocket.send_str(ping_message)
        await asyncio.sleep(20)

async def handle_server_message(response, websocket, device_id, user_id, proxy):
    try:
        message = json.loads(response)
        logger.info(f"Received message: {message}")
        if message.get("action") == "AUTH":
            await send_auth_response(websocket, message, device_id, user_id)
        elif message.get("action") == "PONG":
            await send_pong_response(websocket, message)
            await update_proxy_status(proxy)
    except json.JSONDecodeError:
        logger.error(f"Failed to decode message: {response}")

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
    await websocket.send_str(json.dumps(auth_response))

async def send_pong_response(websocket, message):
    pong_response = {"id": message["id"], "origin_action": "PONG"}
    logger.debug(f"Sending pong response: {pong_response}")
    await websocket.send_str(json.dumps(pong_response))

async def update_proxy_status(proxy):
    with open("active_proxies.txt", "a") as file:
        file.write(proxy[len("socks5://"):].strip() + "\n")
    logger.info(f"Proxy list updated with: {proxy}")

async def handle_proxy_error(proxy):
    logger.info(f"Proxy error encountered, marking {proxy} as invalid.")
    await remove_proxy_from_file("user_proxy.txt", proxy[len("socks5://"):])

async def remove_proxy_from_file(file_path, proxy):
    if proxy.startswith("socks5://"):
        proxy = proxy[len("socks5://"):].strip()
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
    
    max_connections = 30 
    semaphore = asyncio.Semaphore(max_connections)

    connection_tasks = [asyncio.create_task(connect_to_websocket(proxy, user_id, semaphore)) for proxy in proxies]
    await asyncio.gather(*connection_tasks)

if __name__ == "__main__":
    asyncio.run(main())
