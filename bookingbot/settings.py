
import datetime

from babel import Locale
from bookingbot.store import Store
from babel.dates import format_date

class Settings:
    def __init__(self):
        self.store = Store[dict](f"data/settings.json", {})
        
    def set_timezone(self, user_id: str, timezone: str):
        if not self.store.data.get(str(user_id)):
            self.store.data[str(user_id)] = {}
        
        self.store.data[str(user_id)]["timezone"] = timezone
        self.store.sync()
        
    def get_timezone(self, user_id: str):
        return self.store.data.get(str(user_id), {}).get("timezone")
    
    def set_locale(self, user_id: str, locale: str):
        if not self.store.data.get(str(user_id)):
            self.store.data[str(user_id)] = {}
        
        self.store.data[str(user_id)]["locale"] = locale
        self.store.sync()
        
    def get_locale(self, user_id: str):
        territory = self.store.data.get(str(user_id), {}).get("locale")
        if not territory:
            return None
        return Locale("en",  territory)
    
    def is_month_first(self, user_id: str):
        locale = self.get_locale(user_id)
        if not locale:
            return False
        
        return self.__is_month_first(locale)

    def __is_month_first(self, locale):
        date = datetime.date(2022, 10, 25)  # A date where day and month are different
        formatted_date = format_date(date, "short", locale=locale)
        # Split the date string and check if the first part is the month
        return formatted_date.split('/')[0] == '10'