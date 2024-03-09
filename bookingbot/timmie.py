
from bookingbot.store import Store


class Timmie:
    
    def __init__(self):
        self.timmies = Store[dict](f"data/timmie.json", {})
        
    def add(self, timmie_id: str, instructor_id: str):
        if not self.timmies.data.get(timmie_id):
            self.timmies.data[timmie_id] = []
            
        if instructor_id in self.timmies.data[timmie_id]:
            return
        
        self.timmies.data[timmie_id].append(instructor_id)
        self.timmies.sync()
        
    def remove(self, timmie_id: str, instructor_id: str):
        if not self.timmies.data.get(timmie_id):
            return
        
        self.timmies.data[timmie_id] = [instructor for instructor in self.timmies.data[timmie_id] if instructor != instructor_id]
        self.timmies.sync()
        
    def clear(self, timmie_id: str):
        if not self.timmies.data.get(timmie_id):
            return
        
        del self.timmies.data[timmie_id]
        self.timmies.sync()
        
    def list_instructors(self, timmie_id: str):
        return self.timmies.data.get(timmie_id, [])
    
    def list_timmies(self, instructor_id: str):
        return [timmie_id for timmie_id, instructors in self.timmies.data.items() if instructor_id in instructors]