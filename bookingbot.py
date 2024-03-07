import discord

import logging
from logging.handlers import RotatingFileHandler
import os

from bookingbot import Config, Commands


os.makedirs("data/logs", exist_ok=True)
filehandler = RotatingFileHandler(filename="data/logs/bookingbot.log", mode="w", maxBytes=1024 * 50, backupCount=4)

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(name)s - %(levelname)s:%(message)s",
                    handlers=[filehandler])

bot = discord.Bot()

bot.add_cog(Commands(bot))

bot.run(Config().token)