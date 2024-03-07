import logging
import os
import shutil
from typing import Union
import uuid
import pytz

import discord

from bookingbot import Store, Timeslots
from discord import Cog, Option, guild_only, slash_command
from discord.commands import default_permissions


_log = logging.getLogger(__name__)


class Commands(Cog):
    
    def __init__(self, bot):
        self.timezones = Store[dict](f"data/timezones.json", {})
        self.timeslots = Timeslots()
        self.bot = bot
    
    async def autocomplete_timezone(self, ctx: discord.AutocompleteContext):
        return [tz for tz in pytz.all_timezones if ctx.value.lower() in tz.lower()][:25]

    @slash_command()
    @guild_only()
    async def set_timezone(
        self,
        ctx: discord.ApplicationContext,
        timezone: Option(
            str, "Your timezone", required=True, autocomplete=autocomplete_timezone
        ),
    ):
        """Set your timezone."""
        # Get the user ID
        user_id = ctx.author.id

        # Get the selected timezone
        selected_timezone = timezone

        # Save the timezone for the user
        self.timezones.data[str(user_id)] = selected_timezone
        self.timezones.sync()

        # Send a confirmation message
        await ctx.respond(f"Your timezone has been set to {selected_timezone}.", ephemeral=True)
        
    
        
    