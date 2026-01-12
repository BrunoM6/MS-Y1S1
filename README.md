# Residential Energy Model

Agent-Based Model (ABM) simulating household energy consumption patterns using Mesa framework.

## Project Overview

This simulation models a residential dwelling with occupants, appliances, and varying environmental conditions to analyze energy consumption under different scenarios. The model tests three key hypotheses about smart appliances, extreme weather impacts, and insulation effectiveness.

### Key Features
- **Agent-based simulation** of household behavior and energy use
- **Dynamic weather scenarios** (normal, heatwave, cold snap)
- **Smart appliance configurations** with varying automation levels
- **Real-time visualization** via Mesa web interface
- **Hypothesis testing framework** for energy efficiency analysis
- **Integration with real data** (Open-Meteo weather, REN electricity pricing)

## Requirements

- **Python version:** 3.10.12
- **Mesa version:** 2.4.0

## Installation

1. **Clone the repository**
2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```
3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
4. **Run the model**
   ```bash
   python interface.py
   ```
5. **Access the web interface** and customize parameters as needed.

