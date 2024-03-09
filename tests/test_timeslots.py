import unittest
from unittest.mock import MagicMock
from bookingbot.timeslots import Timeslots
import time

class TimeslotsTests(unittest.TestCase):
    def setUp(self):
        self.timmies = MagicMock()
        self.timeslots = Timeslots(self.timmies)
        self.timeslots.timeslots = MagicMock()
        self.timeslots.timeslots.data = []
        self.future_time = int(time.time()) + 3600
        self.past_time = int(time.time()) - 3600

    def test_add_timeslot(self):
        timeslot = {"id": "1", "time": self.future_time, "instructor": "1234567890", "booking": {}}
        self.timeslots.add(timeslot)
        self.assertEqual(len(self.timeslots.timeslots.data), 1)
        self.timeslots.timeslots.sync.assert_called_once()

    def test_list_timeslots(self):
        timeslot1 = {"id": "1", "time": self.future_time, "instructor": "1234567890", "booking": {}}
        timeslot2 = {"id": "2", "time": self.future_time, "instructor": "1234567890", "booking": {}}
        self.timeslots.add(timeslot1)
        self.timeslots.add(timeslot2)
        timeslots = self.timeslots.list()
        self.assertEqual(len(timeslots), 2)

    def test_remove_timeslot(self):
        timeslot = {"id": "1", "time": self.future_time, "instructor": "1234567890", "booking": {}}
        self.timeslots.add(timeslot)
        self.timeslots.timeslots.sync.reset_mock()
        self.timeslots.remove("1")
        self.assertEqual(len(self.timeslots.timeslots.data), 0)
        self.timeslots.timeslots.sync.assert_called_once()

    def test_has_booking(self):
        timeslot = {"id": "1", "time": self.future_time, "instructor": "1234567890", "booking": {"user_id": "1234567890"}}
        self.timeslots.add(timeslot)
        self.assertTrue(self.timeslots.has_booking("1234567890"))
        self.assertFalse(self.timeslots.has_booking("9876543210"))

    def test_is_available(self):
        timeslot = {"id": "1", "time": self.future_time, "instructor": "1234567890", "booking": {}}
        self.timeslots.add(timeslot)
        self.assertTrue(self.timeslots.is_available("1"))
        self.assertFalse(self.timeslots.is_available("2"))

    def test_book_timeslot(self):
        timeslot = {"id": "1", "time": self.future_time, "instructor": "1234567890", "booking": {}}
        booking_data = {"user_id": "1234567890", "meta_username": "meta", "got_username": "got"}
        self.timeslots.add(timeslot)
        self.timeslots.book("1", booking_data)
        self.assertEqual(self.timeslots.timeslots.data[0]["booking"], booking_data)

    def test_exists_timeslot(self):
        timeslot = {"id": "1", "time": self.future_time, "instructor": "1234567890", "booking": {}}
        self.timeslots.add(timeslot)
        self.assertTrue(self.timeslots.exists("1"))
        self.assertFalse(self.timeslots.exists("2"))
        
    def test_cleanup_timeslots(self):
        timeslot1 = {"id": "1", "time": self.future_time, "instructor": "1234567890", "booking": {}}
        timeslot2 = {"id": "2", "time": self.future_time, "instructor": "1234567890", "booking": {}}
        timeslot3 = {"id": "3", "time": self.future_time, "instructor": "1234567890", "booking": {}}
        self.timeslots.add(timeslot1)
        self.timeslots.add(timeslot2)
        self.assertEqual(len(self.timeslots.timeslots.data), 2)
        self.timeslots.timeslots.data[0]["time"] = self.past_time
        self.timeslots.add(timeslot3)
        self.assertEqual(len(self.timeslots.timeslots.data), 2)
        self.timeslots.timeslots.sync.assert_called()

if __name__ == "__main__":
    unittest.main()
        
