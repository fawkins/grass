import os

async def main():
    user_id = None
    # Check if the user_id.txt file exists
    if os.path.exists("user_id.txt"):
        with open("user_id.txt", "r") as file:
            user_id = file.read().strip()
    else:
        logger.error("user_id.txt file not found. Please create the file with a valid user ID.")
        return

    with open("user_proxy.txt", "r") as file:
        proxies = [
            f'socks5://{line.strip()}' if not line.startswith("socks5://") else line.strip()
            for line in file
        ]

    connection_tasks = [asyncio.create_task(connect_to_websocket(proxy, user_id)) for proxy in proxies]
    await asyncio.gather(*connection_tasks)
