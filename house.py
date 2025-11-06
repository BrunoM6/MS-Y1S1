import random
from typing import List, Optional, Dict
import mesa
from enums import RoomType, ApplianceType

class Room(mesa.Agent):
    def __init__(self, unique_id, model, room_type: RoomType, has_window: bool, temperature: float = 20.0, lights_on: bool = False):
        super().__init__(unique_id, model)
        self.room_type = room_type
        self.temperature = temperature
        self.has_window = has_window
        self.lights_on = lights_on
        self.occupants: List = []
        self.appliances: List = []

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
        # Smart appliances should auto-turn-off when room empty
        if not self.occupants:
            for appliance in self.appliances:
                if appliance.is_smart:
                    appliance.turn_off()

# POWER_CONSUMPTION uses ApplianceType defined in enums.py
class Appliance(mesa.Agent):
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

    def __init__(self, unique_id, model, appliance_type: ApplianceType, room: Room, is_smart: bool = False):
        super().__init__(unique_id, model)
        self.appliance_type = appliance_type
        self.room = room
        self.is_on = False
        self.is_smart = is_smart
        self.power_consumption = self.POWER_CONSUMPTION[appliance_type]
        self.hours_used = 0.0
        self.total_consumption = 0.0

        # Refrigerator and water heater are always on
        if appliance_type in [ApplianceType.REFRIGERATOR, ApplianceType.WATER_HEATER]:
            self.is_on = True

        room.appliances.append(self)

    def turn_on(self):
        self.is_on = True

    def turn_off(self):
        # Some appliances stay on
        if self.appliance_type not in [ApplianceType.REFRIGERATOR, ApplianceType.WATER_HEATER]:
            self.is_on = False

    def step(self):
        if self.is_on:
            consumption = self.power_consumption  # 1 step = 1 hour assumption
            self.total_consumption += consumption
            self.hours_used += 1.0
            # model-level aggregator
            if hasattr(self.model, "total_energy_consumed"):
                self.model.total_energy_consumed += consumption
            print(f"[Appliance] {self.appliance_type.name} in {self.room.room_type.name} consumed {consumption} kWh this step.")

class House(mesa.Agent):
    def __init__(self, unique_id, model, num_occupants: int = 2, insulation_quality: float = 0.5, n_kitchens: int = 1, n_living_rooms: int = 1, n_bedrooms: int = 2 ,n_bathrooms: int = 1, n_hallways: int = 1):
        super().__init__(unique_id, model)
        self.insulation_quality = insulation_quality
        self.indoor_temperature = 20.0
        self.rooms: List[Room] = []
        self.occupants = []
        self.total_consumption = 0.0

        # Create rooms
        number_of_rooms: Dict[RoomType, int] = {
            RoomType.KITCHEN: n_kitchens,
            RoomType.LIVING_ROOM: n_living_rooms,
            RoomType.BEDROOM: n_bedrooms,
            RoomType.BATHROOM: n_bathrooms,
            RoomType.HALLWAY: n_hallways
        }

        for room_type, count in number_of_rooms.items():
            for _ in range(count):
                has_window = room_type in [RoomType.KITCHEN, RoomType.LIVING_ROOM, RoomType.BEDROOM]
                room = Room(self.model.next_id(), self.model, room_type, has_window)
                self.rooms.append(room)
                self.model.schedule.add(room)
                self._add_appliances_to_room(room)

        # Create occupants
        self._create_occupants(num_occupants)

    def _add_appliances_to_room(self, room: Room):
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
            # define smart appliances (lights, mobile chargers) per policy
            is_smart = appliance_type in [ApplianceType.LIGHTS, ApplianceType.MOBILE_CHARGER]
            appliance = Appliance(self.model.next_id(), self.model, appliance_type, room, is_smart=is_smart)
            self.model.schedule.add(appliance)

    def _create_occupants(self, num_occupants: int):
        # local import to avoid import order issues in some execution contexts
        from person import Person
        for i in range(num_occupants):
            person = Person(self.model.next_id(), self.model, f"Person_{i}", self)
            self.occupants.append(person)
            self.model.schedule.add(person)

    def get_room_by_type(self, room_type: RoomType) -> Optional[Room]:
        for room in self.rooms:
            if room.room_type == room_type:
                return room
        return None

    def update_temperature(self):
        weather = self.model.get_current_weather()
        for room in self.rooms:
            room.update_temperature(weather.temperature, self.insulation_quality)

    def step(self):
        self.update_temperature()
        # let rooms enforce smart policies
        for room in self.rooms:
            room.step()
