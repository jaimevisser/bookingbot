import logging
import os
import random
import shutil
import string
from typing import Union
import uuid
import pytz
import datetime

import discord

from bookingbot import Store, Timeslots, BookingModal
from discord import Cog, Option, Permissions, User, guild_only, slash_command
from discord.commands import default_permissions


_log = logging.getLogger(__name__)


class Commands(Cog):
    
    def __init__(self, bot):
        self.timezones = Store[dict](f"data/timezones.json", {})
        self.timeslots = Timeslots()
        self.bot = bot
        
    timeslots = discord.SlashCommandGroup(
        name="timeslot",
        description="Timeslot management",
        default_member_permissions=Permissions(administrator=True),
        guild_ids=[1215223314151374849])
    
    async def autocomplete_timezone(self, ctx: discord.AutocompleteContext):
        return [tz for tz in pytz.all_timezones if ctx.value.lower() in tz.lower()][:25]
    
    def generate_identifier(self):
        """Generate a random 5 character identifier excluding 'o', 'O', and '0'."""
        characters = string.ascii_letters + string.digits
        characters = characters.replace('o', '').replace('O', '').replace('0', '')
        return ''.join(random.choices(characters, k=5))

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
        
    
    @timeslots.command(name="add")
    async def add(self, ctx: discord.ApplicationContext, timeslot: str):
        """Add a timeslot. Use `HH:MM` for today or `DD/MM HH:MM` for a specific date."""
        # Get the user ID
        user_id = ctx.author.id

        # Get the user's timezone
        user_timezone = self.timezones.data.get(str(user_id))

        # If the user has not set their timezone, send an error message
        if not user_timezone:
            await ctx.respond("You need to set your timezone first.", ephemeral=True)
            return

        # Get the current time in the user's timezone
        current_time = pytz.utc.localize(datetime.datetime.utcnow()).astimezone(pytz.timezone(user_timezone))

        # Parse the timeslot
        try:
            if ":" in timeslot and "/" not in timeslot:
                # HH:MM format
                hour, minute = map(int, timeslot.split(":"))
                start_time = current_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
                if start_time < current_time:
                    # Add a day if the timeslot is earlier than now
                    start_time += datetime.timedelta(days=1)
            else:
                # DD/MM HH:MM format
                date, time = timeslot.split(" ")
                day, month = date.split("/")
                hour, minute = map(int, time.split(":"))
                start_time = current_time.replace(day=int(day), month=int(month), hour=hour, minute=minute, second=0, microsecond=0)
                if start_time < current_time:
                    # Add a year if the date is before today
                    start_time = start_time.replace(year=current_time.year + 1)
        except (ValueError, IndexError):
            await ctx.respond("Invalid timeslot format. Please use either `HH:MM` or `DD/MM HH:MM`.", ephemeral=True)
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
        await ctx.respond(f"Timeslot added: <t:{int(start_time.timestamp())}:f>.", ephemeral=True)
        
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
        
    def render_timeslots(self, timeslots):
        message = ""
        for timeslot in timeslots:
            # Add the timeslot to the message with discord timestamp and instructor tag
            message += f"- ID:`{timeslot['id']}` <t:{int(timeslot['time'])}:f> (BOA: <@{timeslot['instructor']}>)"
            # If the timeslot is booked, add the booking information
            if timeslot.get("booking"):
                booking = timeslot["booking"]
                message += f" - Booked by <@{booking['user_id']}> (GOT: `{booking['got_username']}`, Meta: `{booking['meta_username']}`)"
            message += "\n"
        return message
        
    @timeslots.command(name="remove")
    async def remove_timeslot(self, ctx: discord.ApplicationContext, timeslot_id: str):
        """Command to remove a timeslot."""
        
        self.timeslots.remove(timeslot_id)
        
        # Send a confirmation message
        await ctx.respond("Timeslot removed.", ephemeral=True)
        
    @slash_command(name="timeslots")
    async def timeslots_open(self, ctx: discord.ApplicationContext):
        """List all open timeslots."""
        # Get all timeslots
        all_timeslots = self.timeslots.list_open()
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
            success = self.timeslots.book(timeslot_id, booking_data)
            if success:
                await interaction.response.send_message("Timeslot booked successfully.", ephemeral=True)
                
                #Send a message to a specific discord channel when a timeslot is booked
                channel = self.bot.get_channel(1215223888854917121)  # Replace with your channel ID
                await channel.send(f"Timeslot booked by <@{user_id}>: {booking_data['meta_username']}, {booking_data['got_username']}")
                
            else:
                await interaction.response.send_message("Failed to book timeslot", ephemeral=True)

        # Show the booking modal to the user
        modal = BookingModal(callback, title="Book timeslot")
        await ctx.send_modal(modal)
