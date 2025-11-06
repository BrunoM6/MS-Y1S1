import random
import mesa
from typing import Dict, Optional, TYPE_CHECKING, List
from enums import RoomType, ApplianceType

if TYPE_CHECKING:
    from house import House, Room, Appliance


def _generate_routine() -> Dict[int, str]:
    routine = {}
    for h in range(0, 7):
        routine[h] = "sleeping"
    for h in range(7, 9):
        routine[h] = "morning_routine"
    for h in range(9, 12):
        routine[h] = "away"
    for h in range(12, 14):
        routine[h] = "lunch"
    for h in range(14, 18):
        routine[h] = "away"
    for h in range(18, 22):
        routine[h] = "evening_activities"
    for h in range(22, 24):
        routine[h] = "sleeping"
    return routine


class Person(mesa.Agent if False else object):  # keep simple for tests / not running as Mesa agent strictly
    def __init__(self, unique_id, model, name: str, house: 'House'):
        # If Mesa Agent is available, subclass integration can be added; simplified constructor here
        self.unique_id = unique_id
        self.model = model
        self.name = name
        self.house = house
        self.current_room: Optional['Room'] = None
        self.is_home = True
        self.energy_conscious = random.random() > 0.5
        self.routine_schedule = _generate_routine()

    def move_to_room(self, room: 'Room'):
        if self.current_room and self.current_room != room:
            try:
                self.current_room.occupants.remove(self)
            except ValueError:
                pass
            # energy conscious people turn off lights when leaving
            if self.energy_conscious and not self.current_room.occupants:
                for appliance in self.current_room.appliances:
                    if appliance.appliance_type == ApplianceType.LIGHTS:
                        appliance.turn_off()

        self.current_room = room
        if self not in room.occupants:
            room.occupants.append(self)

        hour = self.model.hour_of_day
        if hour < 7 or hour > 19 or (not getattr(room, "has_window", True)):
            for appliance in room.appliances:
                if appliance.appliance_type == ApplianceType.LIGHTS:
                    appliance.turn_on()

    def perform_activity(self, activity: str):
        hour = self.model.hour_of_day

        if activity == "sleeping":
            bedroom = self.house.get_room_by_type(RoomType.BEDROOM)
            if bedroom and self.current_room != bedroom:
                self.move_to_room(bedroom)

        elif activity == "away":
            if self.current_room:
                try:
                    self.current_room.occupants.remove(self)
                except ValueError:
                    pass
                self.current_room = None
            self.is_home = False

        elif activity == "morning_routine":
            self.is_home = True
            if random.random() > 0.5:
                bathroom = self.house.get_room_by_type(RoomType.BATHROOM)
                if bathroom:
                    self.move_to_room(bathroom)
            if 7 <= hour <= 8:
                kitchen = self.house.get_room_by_type(RoomType.KITCHEN)
                if kitchen:
                    self.move_to_room(kitchen)
                    for appliance in kitchen.appliances:
                        if appliance.appliance_type == ApplianceType.STOVE:
                            if random.random() > 0.7:
                                appliance.turn_on()

        elif activity == "lunch":
            self.is_home = True
            # lunch use stove or order out
            if random.random() > 0.4:
                kitchen = self.house.get_room_by_type(RoomType.KITCHEN)
                if kitchen:
                    self.move_to_room(kitchen)
                    for appliance in kitchen.appliances:
                        if appliance.appliance_type == ApplianceType.STOVE and random.random() > 0.5:
                            appliance.turn_on()
            else:
                # ordering out - no appliance use
                pass

        elif activity == "evening_activities":
            self.is_home = True
            if 19 <= hour <= 21:
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
                living_room = self.house.get_room_by_type(RoomType.LIVING_ROOM)
                if living_room:
                    self.move_to_room(living_room)
                    for appliance in living_room.appliances:
                        if appliance.appliance_type == ApplianceType.TV and random.random() > 0.3:
                            appliance.turn_on()

            # Charge mobile devices occasionally
            if random.random() > 0.7:
                for room in self.house.rooms:
                    for appliance in room.appliances:
                        if appliance.appliance_type == ApplianceType.MOBILE_CHARGER:
                            appliance.turn_on()

    def respond_to_temperature(self):
        if not self.is_home or not self.current_room:
            return

        temp = self.current_room.temperature

        # Internal regulation policy specified: keep between 17 and 23 when occupied
        if temp < 17:
            for appliance in self.current_room.appliances:
                if appliance.appliance_type == ApplianceType.HEATER:
                    appliance.turn_on()
        elif temp > 23:
            for appliance in self.current_room.appliances:
                if appliance.appliance_type == ApplianceType.AIR_CONDITIONER:
                    appliance.turn_on()
        else:
            for appliance in self.current_room.appliances:
                if appliance.appliance_type in [ApplianceType.HEATER, ApplianceType.AIR_CONDITIONER]:
                    appliance.turn_off()

    def step(self):
        hour = self.model.hour_of_day
        activity = self.routine_schedule.get(hour, "evening_activities")
        self.perform_activity(activity)
        self.respond_to_temperature()
