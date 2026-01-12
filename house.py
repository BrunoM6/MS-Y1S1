from typing import List, Optional, Dict
import mesa
from enums import RoomType, ApplianceType

"""
This module defines the House, Room, and Appliance classes for the Residential Energy Model.
"""

class Room(mesa.Agent):
    """
    Agent representing a room in the house.

    Attributes:
        room_type (RoomType): Type of the room (e.g., KITCHEN, BEDROOM).
        temperature (float): Current temperature of the room in Celsius.
        has_window (bool): Indicates if the room has a window.
        lights_on (bool): Indicates if the lights are on.
        occupants (List): List of occupants currently in the room.
        appliances (List): List of appliances in the room.
    """
    def __init__(self, unique_id, model, room_type: RoomType, has_window: bool, temperature: float = 20.0, lights_on: bool = False):
        """Initialize a room with given parameters."""
        super().__init__(unique_id, model)
        self.room_type = room_type
        self.temperature = temperature
        self.has_window = has_window
        self.lights_on = lights_on
        self.occupants: List = []
        self.appliances: List = []

    def update_temperature(self, external_temp: float, house_insulation: float):
        """Update the room temperature based on external conditions, insulation and appliance usage."""
        # 1. Passive Physics
        exchange_rate = (1 - house_insulation) * 0.05 
        temp_diff = external_temp - self.temperature
        self.temperature += temp_diff * exchange_rate

        # 2. Smart Occupancy Targets
        if len(self.occupants) > 0:
            TARGET_HEAT = 20.0
            TARGET_COOL = 23.0
        else:
            TARGET_HEAT = 12.0 
            TARGET_COOL = 28.0 

        TOLERANCE = 1.0 

        for appliance in self.appliances:
            
            # --- HEATER LOGIC ---
            if appliance.appliance_type == ApplianceType.HEATER:
                
                is_heating = getattr(appliance, 'hysteresis_active', False)

                # ON
                if self.temperature < (TARGET_HEAT - TOLERANCE):
                    appliance.turn_on()
                    appliance.hysteresis_active = True
                    is_heating = True
                # OFF
                elif self.temperature > (TARGET_HEAT + TOLERANCE):
                    appliance.turn_off()
                    appliance.current_load = 0.0
                    appliance.hysteresis_active = False
                    is_heating = False

                if is_heating:
                    needed = (TARGET_HEAT + TOLERANCE) - self.temperature
                    
                    
                    max_power = 2.5 
                    
                    if self.temperature < 5.0: max_power *= 2.0 # Turbo for freezing rooms
                    
            
                    actual_change = min(needed, max_power)
                    self.temperature += actual_change
                    
                   
                    # Ex: Load = 0.5 / 2.5 = 0.2 (20% power usage) -> Cost = 0.4 kWh
                    appliance.current_load = actual_change / max_power

            # --- A/C LOGIC ---
            elif appliance.appliance_type == ApplianceType.AIR_CONDITIONER:
                is_cooling = getattr(appliance, 'hysteresis_active', False)

                if self.temperature > (TARGET_COOL + TOLERANCE):
                    appliance.turn_on()
                    appliance.hysteresis_active = True
                    is_cooling = True
                elif self.temperature < (TARGET_COOL - TOLERANCE):
                    appliance.turn_off()
                    appliance.current_load = 0.0
                    appliance.hysteresis_active = False
                    is_cooling = False

                if is_cooling:
                    needed = self.temperature - (TARGET_COOL - TOLERANCE)
                    
                    # Restore AC capacity
                    max_power = 3.0 
                    
                    actual_change = min(needed, max_power)
                    self.temperature -= actual_change
                    appliance.current_load = actual_change / max_power

    def step(self):
        """Execute one simulation step: auto-turn-off smart appliances if room is empty."""
        # Smart appliances should auto-turn-off when room empty
        if not self.occupants:
            for appliance in self.appliances:
                if appliance.is_smart:
                    appliance.turn_off()

class Appliance(mesa.Agent):
    """
    Agent representing an appliance in the house.

    Attributes:
        appliance_type (ApplianceType): Type of the appliance (e.g., REFRIGERATOR, STOVE).
        room (Room): The room where the appliance is located.
        is_on (bool): Indicates if the appliance is currently on.
        is_smart (bool): Indicates if the appliance has smart capabilities.
        power_consumption (float): Power consumption rate in kWh.
        hours_used (float): Total hours the appliance has been used.
        total_consumption (float): Total energy consumed in kWh.
        current_load (float): Current load percentage (for appliances with variable power).
    """


    # POWER_CONSUMPTION uses ApplianceType defined in enums.py
    POWER_CONSUMPTION = {
        ApplianceType.REFRIGERATOR: 0.15,
        ApplianceType.STOVE: 2.0,
        ApplianceType.WASHING_MACHINE: 1.5,
        ApplianceType.DISHWASHER: 1.2,
        ApplianceType.TV: 0.15,
        ApplianceType.COMPUTER: 0.2,
        ApplianceType.LIGHTS: 0.06,
        ApplianceType.HEATER: 2.0,
        ApplianceType.AIR_CONDITIONER: 2.5,
        ApplianceType.WATER_HEATER: 0.00116, # energy (kWh) to heat 1L of water (kWh/L/°C)
        ApplianceType.MOBILE_CHARGER: 0.01
    }

    def __init__(self, unique_id, model, appliance_type: ApplianceType, room: Room, is_smart: bool = False):
        """Initialize an appliance with given parameters in a given room."""
        super().__init__(unique_id, model)
        self.appliance_type = appliance_type
        self.room = room
        self.is_on = False
        self.is_smart = is_smart
        self.power_consumption = self.POWER_CONSUMPTION[appliance_type]
        self.hours_used = 0.0
        self.total_consumption = 0.0
        self.current_load = 0.0

        # Start an Appliance cycle
        self.cycle_duration = 0  # hours remaining in current cycle
        self.cycle_energy_per_hour = 0.0

        # Refrigerator and water heater are always on
        if appliance_type in [ApplianceType.REFRIGERATOR, ApplianceType.WATER_HEATER]:
            self.is_on = True

        # Smart appliance tracking variables
        if self.is_smart:
            self.is_being_used = False
            self.inactive_time = 0
            self.max_idle_time = 2

        room.appliances.append(self)

    def start_cycle(self, duration_hours: int = 2):
            if not self.is_on:
                self.turn_on()
                self.cycle_duration = duration_hours
                # Per hour consumption
                if self.appliance_type == ApplianceType.STOVE:
                    self.cycle_energy_per_hour = self.power_consumption
                # Distributed consumption
                else:
                    # Distribute total energy over the duration
                    self.cycle_energy_per_hour = self.power_consumption / duration_hours

    def _get_occupant_count(self):
        """Getter for the number of occupants."""
        count = 0
        for agent in self.model.schedule.agents:
            if agent.__class__.__name__ == "Person":
                count += 1
        return count if count > 0 else 1

    def turn_on(self):
        """Turn on the appliance and mark it as being used if smart."""
        self.is_on = True
        # Mark smart appliance as used (resets idle timer for smart appliances)
        if self.is_smart:
            self.is_being_used = True
            self.inactive_time = 0

    def turn_off(self):
        """Turn off the appliance unless it's a refrigerator or water heater."""
        # Some appliances stay on
        if self.appliance_type not in [ApplianceType.REFRIGERATOR, ApplianceType.WATER_HEATER]:
            self.is_on = False

    def step(self):
        """Execute one simulation step: calculate energy consumption and manage smart appliance logic."""
        # Reset usage flag for next step
        if self.is_smart:
            self.is_being_used = False

        # If appliance is smart, is turned on and isn't being used start idle timer logic
        if self.is_smart and self.is_on and not self.is_being_used:
            self.inactive_time += 1
            if self.inactive_time >= self.max_idle_time:
                self.turn_off()
                print(f"[Appliance] {self.appliance_type.name} in {self.room.room_type.name} auto-turned off due to inactivity.")

        consumption = 0.0
        if self.is_on:
            if self.appliance_type == ApplianceType.REFRIGERATOR:
                # Base consumption is rated at standard room temp (e.g. 20°C)
                # Efficiency drops as outside temp rises.
                # Approx rule: +5% energy per degree above 20°C
                room_temp = self.room.temperature
                
                # Calculate thermodynamic factor (capped to avoid crazy values)
                temp_factor = 1.0 + (max(0, room_temp - 20.0) * 0.05)
                
                consumption = self.power_consumption * temp_factor


            elif self.appliance_type in [ApplianceType.DISHWASHER, ApplianceType.STOVE]:
                # Cycle-based logic
                if self.cycle_duration > 0:
                    step_duration = min(1.0, self.cycle_duration)
                    consumption = self.cycle_energy_per_hour * step_duration
                    self.cycle_duration -= 1
                else:
                    self.turn_off()

            elif self.appliance_type == ApplianceType.WATER_HEATER:
                outside_temp = self.model.get_current_weather().temperature

                n = self._get_occupant_count()
                V_person = 50.0 # average liters used per shower
                T_target = 60.0 # kills bacteria, necessary for safety
                Delta_T = T_target - outside_temp

                room_temp = self.room.temperature
                base_loss = 1.2 # standard loss at 20 C room (kwh)
                loss_factor = 1.0 + (max(0, 20.0 - room_temp) * 0.02) # 2% loss increase for each degree below 20
                L_tank = base_loss * loss_factor

                # apply formula based on water properties
                factor = 0.00116
                E_daily = (n * V_person * Delta_T * factor) + L_tank

                consumption = E_daily / 24

            else:
                # base consumption
                consumption = self.power_consumption
                
                # Dynamic consumption for climate control appliances with graduated scaling
                if self.appliance_type in [ApplianceType.HEATER, ApplianceType.AIR_CONDITIONER]:
                    if hasattr(self, 'current_load') and self.current_load > 0:
                        
                        # Base consumption * Load Factor
                     
                        usage_multiplier = 1.0
                        if self.appliance_type == ApplianceType.HEATER and self.room.temperature < 10:
                            usage_multiplier = 2.0
                        elif self.appliance_type == ApplianceType.AIR_CONDITIONER and self.room.temperature > 30:
                            usage_multiplier = 2.0

                        consumption = self.power_consumption * self.current_load * usage_multiplier
                    
                    else:
                        # Standby consumption (thermostat monitoring)
                        consumption = 0.01
                
            self.total_consumption += consumption
            # model-level aggregator
            if hasattr(self.model, "total_energy_consumed"):
                self.model.total_energy_consumed += consumption
            # Track consumption by appliance
            if hasattr(self.model, "consumption_by_appliance"):
                self.model.consumption_by_appliance[self.appliance_type] += consumption

class House(mesa.Agent):
    """
    Agent representing a house in the residential energy model.

    Attributes:
        insulation_quality (float): Insulation quality of the house (0 to 1).
        indoor_temperature (float): Current indoor temperature of the house.
        rooms (List[Room]): List of rooms in the house.
        occupants (List): List of occupants in the house.
        total_consumption (float): Total energy consumption of the house.
        smart_appliances (str): Smart appliance configuration ("none", "base", "all").
    """
    ROOM_VOLUMES = {
        # Volume weights for each room type
            RoomType.LIVING_ROOM: 0.35, 
            RoomType.BEDROOM: 0.25,
            RoomType.KITCHEN: 0.15,
            RoomType.HALLWAY: 0.10,
            RoomType.BATHROOM: 0.05
        }
    def __init__(self, unique_id, model, num_occupants: int = 2, insulation_quality: float = 0.5, n_kitchens: int = 1, n_living_rooms: int = 1, n_bedrooms: int = 2 ,n_bathrooms: int = 1, n_hallways: int = 1, smart_appliances: str = "base"):
        """Initialize a house with given parameters and create rooms and occupants."""
        super().__init__(unique_id, model)
        self.insulation_quality = insulation_quality
        self.indoor_temperature = 15
        self.rooms: List[Room] = []
        self.occupants = []
        self.total_consumption = 0.0
        self.smart_appliances = smart_appliances

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
        """Populate a room with appliances based on its type and smart appliance settings."""
        appliances_by_room = {
            RoomType.KITCHEN: [
                ApplianceType.REFRIGERATOR,
                ApplianceType.STOVE,
                ApplianceType.DISHWASHER,
                ApplianceType.LIGHTS,
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
                ApplianceType.AIR_CONDITIONER,
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
            # None case: no smart appliances
            if self.smart_appliances == "none":
                is_smart = False
            # All case: Lights, Mobile Charger, TV and Computer are smart
            elif self.smart_appliances == "all":
                is_smart = appliance_type in [ApplianceType.LIGHTS, ApplianceType.MOBILE_CHARGER, ApplianceType.TV, ApplianceType.COMPUTER]
            # Base case: only lights and mobile chargers are smart
            else:
                is_smart = appliance_type in [ApplianceType.LIGHTS, ApplianceType.MOBILE_CHARGER]
            appliance = Appliance(self.model.next_id(), self.model, appliance_type, room, is_smart=is_smart)
            self.model.schedule.add(appliance)

    def _create_occupants(self, num_occupants: int):
        """Create occupants and add them to the house."""
        # local import to avoid import order issues in some execution contexts
        from person import Person
        for i in range(num_occupants):
            person = Person(self.model.next_id(), self.model, f"Person_{i}", self)
            self.occupants.append(person)
            self.model.schedule.add(person)

    def get_room_by_type(self, room_type: RoomType) -> Optional[Room]:
        """Retrieve a room by its type."""
        for room in self.rooms:
            if room.room_type == room_type:
                return room
        return None

    def update_temperature(self):
        """Update the temperature of each room based on external weather conditions."""
        weather = self.model.get_current_weather()
        for room in self.rooms:
            room.update_temperature(weather.temperature, self.insulation_quality)

    def distribute_heat(self):
        """Simulate air circulation and heat distribution among rooms."""

        # Calculate the Weighted Average Temperature of the whole house
        total_volume = 0.0
        weighted_temp_sum = 0.0
        
        for room in self.rooms:
            # Get volume weight
            weight = self.ROOM_VOLUMES.get(room.room_type, 0.1)
            weighted_temp_sum += room.temperature * weight
            total_volume += weight
            
        avg_house_temp = weighted_temp_sum / total_volume

        # 2. Mix the air
        AIR_MIXING_RATE = 0.3 

        for room in self.rooms:
            diff = avg_house_temp - room.temperature
            room.temperature += diff * AIR_MIXING_RATE

    def step(self):
        """Execute one simulation step: update temperatures and enforce smart policies."""
        self.update_temperature()
        # Let rooms enforce smart policies
        for room in self.rooms:
            room.step()

        self.distribute_heat()