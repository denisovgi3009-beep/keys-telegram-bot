# Точка входа для хостингов, которые ищут main.py (Pterodactyl-яйца, некоторые панели)
import asyncio
from bot import main

if __name__ == "__main__":
    asyncio.run(main())
