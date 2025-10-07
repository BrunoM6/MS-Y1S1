from enum import Enum
import mesa


class RoomType(Enum):
    KITCHEN = "kitchen"
    LIVING_ROOM = "living room"
    BEDROOM = "bedroom"
    BATHROOM = "bathroom"
    HALLWAY = "hallway"

class ApplianceType(Enum):
    REFRIGERATOR = "refrigerator"
    STOVE = "stove"
    WASHING_MACHINE = "washing machine"
    DISHWASHER = "dishwasher"
    TV = "tv"
    COMPUTER = "computer"
    LIGHTS = "lights"
    HEATER = "heater"
    AIR_CONDITIONER = "air conditioner"
    WATER_HEATER = "water heater"
    MOBILE_CHARGER = "mobile charger"


class Room(mesa.Agent):    
    def __init__(self, unique_id, model, room_type: RoomType, temperature: float, window_area: float = 0.0, lights_on: bool = False):
        super().__init__(unique_id, model)
        self.room_type = room_type
        self.temperature = temperature
        self.window_area = window_area
        self.lights_on = lights_on
        self.occupants = []
        self.appliances = []
    
    def update_temperature(self, external_temp: float, house_insulation: float):
        exchange_rate = 1 - house_insulation
        temp_diff = external_temp - self.temperature
        self.temperature += temp_diff * exchange_rate
        
        for appliance in self.appliances:
            if appliance.appliance_type == ApplianceType.HEATER and appliance.is_on:
                self.temperature += 0.5
            elif appliance.appliance_type == ApplianceType.AIR_CONDITIONER and appliance.is_on:
                self.temperature -= 0.5
    
    def step(self):
        """Update room state"""
        pass


class Appliance(mesa.Agent):
    """Represents a household appliance"""
    
    # Power consumption in kW when operating
    POWER_CONSUMPTION = {
        ApplianceType.REFRIGERATOR: 0.15,
        ApplianceType.STOVE: 2.5,
        ApplianceType.WASHING_MACHINE: 1.5,
        ApplianceType.DISHWASHER: 1.8,
        ApplianceType.TV: 0.15,
        ApplianceType.COMPUTER: 0.2,
        ApplianceType.LIGHTS: 0.06,
        ApplianceType.HEATER: 2.0,
        ApplianceType.AIR_CONDITIONER: 2.5,
        ApplianceType.WATER_HEATER: 3.0,
        ApplianceType.MOBILE_CHARGER: 0.01
    }
    
    def __init__(self, unique_id, model, appliance_type: ApplianceType, room: Room):
        super().__init__(unique_id, model)
        self.appliance_type = appliance_type
        self.room = room
        self.is_on = False
        self.power_consumption = self.POWER_CONSUMPTION[appliance_type]
        self.hours_used = 0.0
        self.total_consumption = 0.0
        
        # Refrigerator and water heater are always on
        if appliance_type in [ApplianceType.REFRIGERATOR, ApplianceType.WATER_HEATER]:
            self.is_on = True
        
        room.appliances.append(self)
    
    def turn_on(self):
        """Turn on the appliance"""
        self.is_on = True
    
    def turn_off(self):
        """Turn off the appliance"""
        # Some appliances stay on
        if self.appliance_type not in [ApplianceType.REFRIGERATOR, ApplianceType.WATER_HEATER]:
            self.is_on = False
    
    def step(self):
        """Update appliance consumption"""
        if self.is_on:
            # Consumption per step (assuming 1 step = 1 hour)
            consumption = self.power_consumption
            self.total_consumption += consumption
            self.hours_used += 1.0
            self.model.total_energy_consumed += consumption


class Person(mesa.Agent):
    """Represents a person living in the house"""
    
    def __init__(self, unique_id, model, name: str, house: 'House'):
        super().__init__(unique_id, model)
        self.name = name
        self.house = house
        self.current_room: Optional[Room] = None
        self.is_home = True
        self.energy_conscious = random.random() > 0.5  # 50% are energy conscious
        self.routine_schedule = self._generate_routine()
    
    def _generate_routine(self) -> Dict[int, str]:
        """Generate a daily routine for the person"""
        routine = {}
        # Night: sleeping (0-7)
        for h in range(0, 7):
            routine[h] = "sleeping"
        # Morning: home activities (7-9)
        for h in range(7, 9):
            routine[h] = "morning_routine"
        # Day: away at work/school (9-18)
        for h in range(9, 18):
            routine[h] = "away"
        # Evening: home activities (18-22)
        for h in range(18, 22):
            routine[h] = "evening_activities"
        # Night: sleeping (22-24)
        for h in range(22, 24):
            routine[h] = "sleeping"
        return routine
    
    def move_to_room(self, room: Room):
        """Move person to a room"""
        if self.current_room and self.current_room != room:
            self.current_room.occupants.remove(self)
            # Energy conscious people turn off lights when leaving
            if self.energy_conscious and not self.current_room.occupants:
                for appliance in self.current_room.appliances:
                    if appliance.appliance_type == ApplianceType.LIGHTS:
                        appliance.turn_off()
        
        self.current_room = room
        room.occupants.append(self)
        
        # Turn on lights if needed
        hour = self.model.hour_of_day
        if hour < 7 or hour > 19 or (not room.has_window):
            for appliance in room.appliances:
                if appliance.appliance_type == ApplianceType.LIGHTS:
                    appliance.turn_on()
    
    def perform_activity(self, activity: str):
        """Perform an activity based on the time of day"""
        hour = self.model.hour_of_day
        
        if activity == "sleeping":
            bedroom = self.house.get_room_by_type(RoomType.BEDROOM)
            if bedroom and self.current_room != bedroom:
                self.move_to_room(bedroom)
        
        elif activity == "away":
            if self.current_room:
                self.current_room.occupants.remove(self)
                self.current_room = None
            self.is_home = False
        
        elif activity == "morning_routine":
            self.is_home = True
            # Use bathroom, kitchen
            if random.random() > 0.5:
                bathroom = self.house.get_room_by_type(RoomType.BATHROOM)
                if bathroom:
                    self.move_to_room(bathroom)
            
            # Breakfast time - use kitchen appliances
            if 7 <= hour <= 8:
                kitchen = self.house.get_room_by_type(RoomType.KITCHEN)
                if kitchen:
                    self.move_to_room(kitchen)
                    for appliance in kitchen.appliances:
                        if appliance.appliance_type == ApplianceType.STOVE:
                            if random.random() > 0.7:
                                appliance.turn_on()
        
        elif activity == "evening_activities":
            self.is_home = True
            # Dinner time - use kitchen
            if 19 <= hour <= 20:
                kitchen = self.house.get_room_by_type(RoomType.KITCHEN)
                if kitchen:
                    self.move_to_room(kitchen)
                    for appliance in kitchen.appliances:
                        if appliance.appliance_type == ApplianceType.STOVE:
                            appliance.turn_on()
                        elif appliance.appliance_type == ApplianceType.DISHWASHER:
                            if random.random() > 0.8:
                                appliance.turn_on()
            else:
                # Living room activities
                living_room = self.house.get_room_by_type(RoomType.LIVING_ROOM)
                if living_room:
                    self.move_to_room(living_room)
                    for appliance in living_room.appliances:
                        if appliance.appliance_type == ApplianceType.TV:
                            if random.random() > 0.3:
                                appliance.turn_on()
            
            # Charge mobile devices
            if random.random() > 0.7:
                for room in self.house.rooms:
                    for appliance in room.appliances:
                        if appliance.appliance_type == ApplianceType.MOBILE_CHARGER:
                            appliance.turn_on()
    
    def respond_to_temperature(self):
        """React to room temperature"""
        if not self.is_home or not self.current_room:
            return
        
        temp = self.current_room.temperature
        
        # Too cold
        if temp < 18:
            for appliance in self.current_room.appliances:
                if appliance.appliance_type == ApplianceType.HEATER:
                    appliance.turn_on()
        # Too hot
        elif temp > 26:
            for appliance in self.current_room.appliances:
                if appliance.appliance_type == ApplianceType.AIR_CONDITIONER:
                    appliance.turn_on()
        # Comfortable temperature
        else:
            for appliance in self.current_room.appliances:
                if appliance.appliance_type in [ApplianceType.HEATER, ApplianceType.AIR_CONDITIONER]:
                    appliance.turn_off()
    
    def step(self):
        """Update person's behavior"""
        hour = self.model.hour_of_day
        activity = self.routine_schedule.get(hour, "evening_activities")
        self.perform_activity(activity)
        self.respond_to_temperature()


class House(mesa.Agent):
    """Represents a residential house"""
    
    def __init__(self, unique_id, model, num_occupants: int = 2, insulation_quality: float = 0.5):
        super().__init__(unique_id, model)
        self.insulation_quality = insulation_quality  # 0-1, higher = better
        self.indoor_temperature = 20.0
        self.rooms: List[Room] = []
        self.occupants: List[Person] = []
        self.total_consumption = 0.0
        
        # Create rooms
        self._create_rooms()
        
        # Create occupants
        self._create_occupants(num_occupants)
    
    def _create_rooms(self):
        """Create rooms in the house"""
        room_configs = [
            (RoomType.KITCHEN, True),
            (RoomType.LIVING_ROOM, True),
            (RoomType.BEDROOM, True),
            (RoomType.BEDROOM, True),
            (RoomType.BATHROOM, False),
            (RoomType.HALLWAY, False)
        ]
        
        for room_type, has_window in room_configs:
            room = Room(self.model.next_id(), self.model, room_type, has_window)
            self.rooms.append(room)
            self.model.schedule.add(room)
            
            # Add appliances to rooms
            self._add_appliances_to_room(room)
    
    def _add_appliances_to_room(self, room: Room):
        """Add appropriate appliances to a room"""
        appliances_by_room = {
            RoomType.KITCHEN: [
                ApplianceType.REFRIGERATOR,
                ApplianceType.STOVE,
                ApplianceType.DISHWASHER,
                ApplianceType.LIGHTS
            ],
            RoomType.LIVING_ROOM: [
                ApplianceType.TV,
                ApplianceType.LIGHTS,
                ApplianceType.AIR_CONDITIONER
            ],
            RoomType.BEDROOM: [
                ApplianceType.LIGHTS,
                ApplianceType.COMPUTER,
                ApplianceType.MOBILE_CHARGER,
                ApplianceType.HEATER
            ],
            RoomType.BATHROOM: [
                ApplianceType.LIGHTS,
                ApplianceType.WATER_HEATER
            ],
            RoomType.HALLWAY: [
                ApplianceType.LIGHTS
            ]
        }
        
        for appliance_type in appliances_by_room.get(room.room_type, []):
            appliance = Appliance(self.model.next_id(), self.model, appliance_type, room)
            self.model.schedule.add(appliance)
    
    def _create_occupants(self, num_occupants: int):
        """Create occupants for the house"""
        for i in range(num_occupants):
            person = Person(self.model.next_id(), self.model, f"Person_{i}", self)
            self.occupants.append(person)
            self.model.schedule.add(person)
    
    def get_room_by_type(self, room_type: RoomType) -> Optional[Room]:
        """Get a room by its type"""
        for room in self.rooms:
            if room.room_type == room_type:
                return room
        return None
    
    def update_temperature(self):
        """Update house temperature based on weather"""
        weather = self.model.get_current_weather()
        for room in self.rooms:
            room.update_temperature(weather.temperature, self.insulation_quality)
    
    def step(self):
        """Update house state"""
        self.update_temperature()
