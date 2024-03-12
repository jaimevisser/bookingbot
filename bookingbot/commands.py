import logging
import os
import random
import re
import shutil
import string
from typing import Union
import uuid
from babel import Locale
import pytz
import datetime

import discord

from bookingbot import Timeslots, BookingModal
from discord import Cog, Option, Permissions, User, guild_only, slash_command
from discord.commands import default_permissions

from bookingbot.settings import Settings
from bookingbot.timmie import Timmie

_log = logging.getLogger(__name__)

class Commands(Cog):
    
    def __init__(self, bot):
        self.settings = Settings()
        self.timmies = Timmie()
        self.timeslots = Timeslots(self.timmies)
        self.bot = bot
        
    guild_ids = [1215223314151374849]
        
    timeslots = discord.SlashCommandGroup(
        name="timeslot",
        description="Timeslot management",
        default_member_permissions=Permissions(administrator=True),
        guild_ids=guild_ids)
    
    settings = discord.SlashCommandGroup(
        name="set",
        description="User settings",
        default_member_permissions=Permissions(administrator=True),
        guild_ids=guild_ids)
    
    timmies = discord.SlashCommandGroup(
        name="timmie",
        description="Timmie management",
        default_member_permissions=Permissions(administrator=True),
        guild_ids=guild_ids)
    
    async def autocomplete_timezone(self, ctx: discord.AutocompleteContext):
        return [tz for tz in pytz.all_timezones if ctx.value.lower() in tz.lower()][:25]
    
    async def autocomplete_locales(self, ctx: discord.AutocompleteContext):
        return [Locale("en").territories[locale] for locale in Locale("en").territories if len(locale) == 2 and ctx.value.lower() in Locale("en").territories[locale].lower()][:25]
    
    def generate_identifier(self):
        """Generate a random 5 character identifier excluding 'o', 'O', and '0'."""
        characters = string.ascii_letters + string.digits
        characters = characters.replace('o', '').replace('O', '').replace('0', '')
        return ''.join(random.choices(characters, k=5))

    @settings.command(name="timezone")
    async def set_timezone(
        self,
        ctx: discord.ApplicationContext,
        timezone: Option(
            str, "Your timezone", required=True, autocomplete=autocomplete_timezone
        ),
    ):
        """Set your timezone. Use the autocomplete to find your timezone."""
        # Get the user ID
        user_id = ctx.author.id

        # Get the selected timezone
        selected_timezone = timezone

        # Save the timezone for the user
        self.settings.set_timezone(user_id, selected_timezone)

        # Send a confirmation message
        await ctx.respond(f"Your timezone has been set to {selected_timezone}.", ephemeral=True)
        
    def get_territory_code(self, name):
        locale = Locale('en')
        reverse_territories = {v: k for k, v in locale.territories.items()}
        return reverse_territories.get(name)

    @settings.command(name="locale")
    async def set_locale(
        self,
        ctx: discord.ApplicationContext,
        locale: Option(
            str, "Your locale", required=True, autocomplete=autocomplete_locales
        ),
    ):
        """Set your locale. Use the autocomplete to find your locale."""
        # Get the user ID
        user_id = ctx.author.id

        # Get the selected locale
        selected_locale = self.get_territory_code(locale)
        
        # Check if it's possible to make a locale using "en" and the selected territory code
        try:
            Locale("en", selected_locale)
        except Exception as e:
            await ctx.respond(f"Failed to set your locale to {selected_locale}.", ephemeral=True)
            return

        # Save the locale for the user
        self.settings.set_locale(user_id, selected_locale)

        # Send a confirmation message
        await ctx.respond(f"Your locale has been set to {selected_locale}.", ephemeral=True)
        
    
    @timeslots.command(name="add")
    async def add(self, ctx: discord.ApplicationContext, timeslot: str):
        """Add a timeslot. Use `HH:MM`  for today or `DATE HH:MM` for a specific date."""
        # Get the user ID
        user_id = ctx.author.id

        # Get the user's timezone
        user_timezone = self.settings.get_timezone(str(user_id))

        # If the user has not set their timezone, send an error message
        if not user_timezone:
            await ctx.respond("You need to set your timezone first.", ephemeral=True)
            return

        # Get the current time in the user's timezone
        current_time = pytz.utc.localize(datetime.datetime.utcnow()).astimezone(pytz.timezone(user_timezone))
        
        # Parse the timeslot using a regex
        # The timeslot can be in the format HH:MM or DATE HH:MM
        # DATE format is DD/MM or MM/DD, depending on the user's locale
        month_first = self.settings.is_month_first(user_id)
        
        try:
            regex = r"((\d{1,2})[/-](\d{1,2}) )?(\d{1,2}):?(\d{2})"
            date, day, month, hour, minute = re.match(regex, timeslot).groups()
            
            # Swap day and month if the user's locale uses the month first
            if month_first:
                day, month = month, day
                
            start_time = current_time.replace(hour=int(hour), minute=int(minute), second=0, microsecond=0)
            if start_time < current_time:
                # Add a day if the timeslot is earlier than now
                start_time += datetime.timedelta(days=1)
            
            # If the date is provided, set the date and month  
            if date:
                start_time = start_time.replace(day=int(day), month=int(month))
                if start_time < current_time:
                    # Add a year if the date is before today
                    start_time = start_time.replace(year=current_time.year + 1)
        except (ValueError, IndexError):
            month_format = "MM/DD" if month_first else "DD/MM"
            
            await ctx.respond(
                f"Invalid timeslot format. Please use either `HH:MM` or `{month_format} HH:MM`. You can leave out the ':' if you want.", 
                ephemeral=True)
            return

        # Create the timeslot dictionary
        timeslot_dict = {
            "id": self.generate_identifier(),
            "time": start_time.timestamp(),
            "instructor": user_id
        }

        # Add the timeslot
        self.timeslots.add(timeslot_dict)

        # Send a confirmation message
        await ctx.respond(f"Timeslot added:\n" + self.render_timeslots([timeslot_dict]), ephemeral=True)
        
    @timeslots.command(name="list")
    async def list_timeslots(self, ctx: discord.ApplicationContext, boa: Option(User) = None):
        """Command to list all timeslots. If a user is provided, list their timeslots."""
        # Get all timeslots
        if boa is not None:
            all_timeslots = self.timeslots.list(boa.id)
        else:
            all_timeslots = self.timeslots.list()
        # Sort timeslots by time ascending
        all_timeslots.sort(key=lambda x: x["time"])
        # If there are no timeslots, send a message
        if not all_timeslots:
            await ctx.respond("There are no timeslots available.", ephemeral=True)
            return
        # Create a formatted message with the timeslots
        message = "Timeslots:\n" + self.render_timeslots(all_timeslots)
        # Send the message
        await ctx.respond(message, ephemeral=True)
        
    def render_timeslots(self, timeslots: list):
        message = ""
        for timeslot in timeslots:
            # Add the timeslot to the message with discord timestamp and instructor tag
            message += f"- ID:`{timeslot['id']}` <t:{int(timeslot['time'])}:f> (BOA: <@{timeslot['instructor']}>)"
            # If the timeslot is booked, add the booking information
            if timeslot.get("booking"):
                booking = timeslot["booking"]
                message += f" - Booked by <@{booking['user_id']}> (GOT: `{booking['got_username']}`, Meta: `{booking['meta_username'] or 'N/A'}`, timestamp: `<t:{int(timeslot['time'])}:f>`)"
            message += "\n"
        return message
        
    @timeslots.command(name="remove")
    async def remove_timeslot(self, ctx: discord.ApplicationContext, timeslot_id: str):
        """Command to remove a timeslot."""
        
        self.timeslots.remove(timeslot_id)
        
        # Send a confirmation message
        await ctx.respond("Timeslot removed.", ephemeral=True)
        
    @timmies.command(name="add")
    async def add_timmie(self, ctx: discord.ApplicationContext, timmie: Option(User, "The timmie to add", required=True)):
        """Add a timmie for your timeslots."""
        user_id = ctx.author.id
        self.timmies.add(timmie.id, user_id)
        await ctx.respond(f"Timmie <@{timmie.id}> added for <@{user_id}>.", ephemeral=True)
        
    @timmies.command(name="remove")
    async def remove_timmie(self, ctx: discord.ApplicationContext, timmie: Option(User, "The timmie to remove", required=True)):
        """Remove a timmie for your timeslots."""
        user_id = ctx.author.id
        self.timmies.remove(timmie.id, user_id)
        await ctx.respond(f"Timmie <@{timmie.id}> removed for <@{user_id}>.", ephemeral=True)
        
    @timmies.command(name="list")
    async def list_timmies(self, ctx: discord.ApplicationContext, boa: Option(User, "The BOA to list timmies for", required=False) = None):
        """List all timmies. If a user is provided, list their timmies."""
        if boa is not None:
            all_timmies = self.timmies.list_timmies(boa.id)
        else:
            all_timmies = self.timmies.list_timmies(ctx.author.id)
        if not all_timmies:
            await ctx.respond("You don't have any timmies.", ephemeral=True)
            return
        message = "Timmies:\n" + "\n".join([f"- <@{timmie}>" for timmie in all_timmies])
        await ctx.respond(message, ephemeral=True)
        
    @slash_command(name="timeslots")
    async def timeslots_open(self, ctx: discord.ApplicationContext):
        """List all timeslots that are open for you."""
        # Get the user ID
        user_id = ctx.author.id
        
        # If the user already has a booking, don't allow them to book another timeslot
        user_id = ctx.author.id
        if self.timeslots.has_booking(user_id):
            await ctx.respond("You already have a booking.", ephemeral=True)
            return
        
        # Get all timeslots
        all_timeslots = self.timeslots.list_unbooked_for_timmie(user_id)
        # Sort timeslots by time ascending
        all_timeslots.sort(key=lambda x: x["time"])
        # If there are no timeslots, send a message
        if not all_timeslots:
            await ctx.respond("There are no timeslots available.", ephemeral=True)
            return
        # Create a formatted message with the timeslots
        message = "Timeslots:\n" + self.render_timeslots(all_timeslots)
        # Send the message
        await ctx.respond(message, ephemeral=True)
        
    @slash_command()
    async def book(self, ctx: discord.ApplicationContext, timeslot_id: str = None):
        """Book a timeslot. If no timeslot ID is provided, list all available timeslots."""
        # If the user already has a booking, don't allow them to book another timeslot
        user_id = ctx.author.id
        if self.timeslots.has_booking(user_id):
            await ctx.respond("You already have a booking.", ephemeral=True)
            return
        
        # If the timeslot ID is not provided, list all available timeslots
        if timeslot_id is None:
            await self.timeslots_open(ctx)
            return
               
        # If the timeslot does not exist, send an error message
        if not self.timeslots.exists(timeslot_id):
            await ctx.respond("Timeslot does not exist.", ephemeral=True)
            return
        
        # If the timeslot is already booked, don't allow the user to book it
        if not self.timeslots.is_available(timeslot_id):
            await ctx.respond("Timeslot is already booked.", ephemeral=True)
            return
        
        # Use BookingModal to get the user's meta and GOT usernames
        # The callback will book the timeslot
        async def callback(interaction: discord.Interaction, booking_data: dict):
            booking_data["user_id"] = user_id
            # Book the timeslot using the provided meta and GOT usernames
            timeslot = self.timeslots.book(timeslot_id, booking_data)
            if timeslot:
                await interaction.response.send_message("Timeslot booked successfully.", ephemeral=True)
                
                #Send a message to a specific discord channel when a timeslot is booked
                channel = self.bot.get_channel(1215223888854917121)  # Replace with your channel ID
                await channel.send(f"Timeslot booked: \n" + self.render_timeslots([timeslot]))
                
            else:
                await interaction.response.send_message("Failed to book timeslot", ephemeral=True)

        # Show the booking modal to the user
        modal = BookingModal(callback, title="Book timeslot")
        await ctx.send_modal(modal)
