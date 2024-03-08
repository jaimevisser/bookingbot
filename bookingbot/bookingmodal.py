import discord

class BookingModal(discord.ui.Modal):
    def __init__(self, ext_callback, initial_values={}, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.__ext_callback = ext_callback
        self.add_item(
            discord.ui.InputText(label="Ghosts of Tabor username", value=initial_values.get("got_username"))
        )
        self.add_item(
            discord.ui.InputText(label="Meta username (if using meta party voice)", value=initial_values.get("meta_username"), required=False)
        )

    async def callback(self, interaction: discord.Interaction):
        booking_data = {
            "meta_username": self.children[1].value.strip(),
            "got_username": self.children[0].value.strip(),
        }

        await self.__ext_callback(
            interaction,
            booking_data
        )
