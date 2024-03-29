from bookingbot import Store
import datetime

from bookingbot.timmie import Timmie


class Timeslots:
    # This class is responsible for managing timeslots
    # Timeslot data is stored in a JSON file
    # Timeslot dict format: {"id": "unique identifier","time": <posix timestamp>, "instructor": "1234567890", "booking": {}}
    # Booking dict means that a user has booked the timeslot, it's not set if the timeslot is open
    # Booking dict format: {"user_id": "1234567890", "meta_username": "meta", "got_username": "got"}
    
    def __init__(self, timmies: Timmie):
        self.timeslots = Store[list](f"data/timeslots.json", [])
        self.timmies = timmies
        # Initialize any necessary attributes here
        pass

    def add(self, timeslot: dict):
        self.timeslots.data.append(timeslot)
        self.__cleanup()
        self.timeslots.sync()
        
    def list(self, instructor: str = None):
        if instructor is None:
            return self.timeslots.data
        
        return [timeslot for timeslot in self.timeslots.data if timeslot["instructor"] == instructor]
    
    def list_unbooked_for_timmie(self, timmie_id: str):
        timmie_instructors = self.timmies.list_instructors(timmie_id)
        return [timeslot for timeslot in self.timeslots.data if not timeslot.get("booking") and timeslot["instructor"] in timmie_instructors]
    
    def remove(self, timeslot_id: str):
        self.timeslots.data = [timeslot for timeslot in self.timeslots.data if timeslot["id"] != timeslot_id]
        self.__cleanup()
        self.timeslots.sync()
        
    def has_booking(self, user_id: str):
        return any([timeslot for timeslot in self.timeslots.data if timeslot.get("booking", {}).get("user_id") == user_id])
    
    def is_available(self, timeslot_id: str):
        return any([timeslot for timeslot in self.timeslots.data if timeslot["id"] == timeslot_id and not timeslot.get("booking")])
    
    def book(self, timeslot_id: str, booking_data: dict):
        for timeslot in self.timeslots.data:
            if timeslot["id"] == timeslot_id and not timeslot.get("booking"):
                timeslot["booking"] = booking_data
                self.timeslots.sync()
                self.timmies.clear(booking_data["user_id"])
                return timeslot
        return False
    
    def exists(self, timeslot_id: str):
        return any([timeslot for timeslot in self.timeslots.data if timeslot["id"] == timeslot_id])
    
    def __cleanup(self):
        # Remove any expired timeslots
        current_time = datetime.datetime.now()
        self.timeslots.data = [timeslot for timeslot in self.timeslots.data if current_time.timestamp() - timeslot["time"] <= datetime.timedelta(minutes=10).total_seconds()]