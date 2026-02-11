# Clockwork

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/custom-repositories)
[![GitHub release](https://img.shields.io/github/release/mutilator/clockwork.svg)](https://github.com/mutilator/clockwork/releases)
[![GitHub License](https://img.shields.io/github/license/mutilator/clockwork.svg)](LICENSE)

`Clockwork` is a custom integration for [Home Assistant](https://www.home-assistant.io/) that provides advanced date, time, and duration calculations. Create sensors and binary sensors for measuring timespans, checking date ranges, detecting seasons, and triggering time-based automations.

## Features

- **Timespan Calculations**: Calculate duration since an entity changed state, with configurable tracking modes
- **Offset Calculations**: Time-delayed triggers with pulse, duration, and latch modes
- **Datetime Offset**: Apply time offsets to datetime entities for scheduling
- **Date Range Duration**: Measure duration between two datetime entities
- **Season Detection**: Detect current season automatically
- **Month Detection**: Check if current date falls in specified months  
- **Holiday Countdowns**: Built-in US holidays plus custom holiday support
- **Date Range Checks**: Determine if current time is within or outside a range
- **No YAML Required**: All configuration through intuitive Home Assistant UI
- **Real-time Updates**: Configurable update intervals for time-based sensors
- **Flexible Triggering**: Control which state changes trigger offset calculations
- **Timezone Aware**: Automatic timezone handling for datetime comparisons

## Installation

### Via HACS (Recommended)

1. Open HACS in Home Assistant
2. Click "Custom repositories" in the top right
3. Add this repository:
   - **Repository URL**: `https://github.com/mutilator/clockwork`
   - **Category**: Integration
4. Click "Install"
5. In Home Assistant, go to **Settings > Devices & Services**
6. Click **Create Automation** and search for "Clockwork"
7. Follow the setup wizard

### Manual Installation

1. Download the [latest release](https://github.com/mutilator/clockwork/releases)
2. Unzip and copy the `clockwork` folder to:
   ```
   ~/.homeassistant/custom_components/
   ```
3. Restart Home Assistant
4. Go to **Settings > Devices & Services > Create Automation** and search for "Clockwork"

## Configuration

All configuration is done through the Home Assistant UI. No YAML editing required!

1. Go to **Settings > Devices & Services > Clockwork**
2. Select **Configure**
3. Choose from:
   - **Add Calculation** - Create a new sensor or binary sensor
   - **Modify Calculation** - Edit existing calculations
   - **Delete Calculation** - Remove calculations
   - **Add Custom Holiday** - Define custom holidays for countdowns

### Calculation Types

- **Timespan** - Measure duration since state change
- **Offset** - Trigger after elapsed time
- **Datetime Offset** - Apply time offset to datetime
- **Date Range Duration** - Measure duration between two datetimes
- **Season Detection** - Detect spring, summer, autumn, or winter
- **Month Detection** - Check specific months
- **Holiday Countdown** - Days until US holidays or custom dates
- **Between Dates** - True when current time is within range
- **Outside Dates** - True when current time is outside range

## Documentation

Comprehensive documentation with examples and use cases is available in the [GitHub Wiki](https://github.com/mutilator/clockwork/wiki):

- [Getting Started Guide](https://github.com/mutilator/clockwork/wiki/Home)
- [Timespan Calculation](https://github.com/mutilator/clockwork/wiki/Timespan-Calculation)
- [Offset Calculation](https://github.com/mutilator/clockwork/wiki/Offset-Calculation)
- [Datetime Offset](https://github.com/mutilator/clockwork/wiki/Datetime-Offset)
- [Date Range Duration](https://github.com/mutilator/clockwork/wiki/Date-Range-Duration)
- [Season Detection](https://github.com/mutilator/clockwork/wiki/Season-Detection)
- [Month Detection](https://github.com/mutilator/clockwork/wiki/Month-Detection)
- [Holiday Countdown](https://github.com/mutilator/clockwork/wiki/Holiday-Countdown)
- [Custom Holidays](https://github.com/mutilator/clockwork/wiki/Custom-Holidays)
- [Between/Outside Dates](https://github.com/mutilator/clockwork/wiki/Between-Dates-Check)

Each wiki page includes detailed configuration instructions, real-world examples, and automation templates.

## Quick Example

To see Clockwork in action:

1. Install the integration
2. Create a **Timespan Calculation** for a door sensor:
   - Name: "Door Open Duration"
   - Entity: Your door sensor
   - Track State: "on"
3. Use in an automation to alert if door is open for 30+ minutes:
   ```yaml
   condition:
     - condition: numeric_state
       entity_id: sensor.door_open_duration
       above: 1800  # 30 minutes in seconds
   ```

For more examples and walkthroughs, see the [wiki](https://github.com/mutilator/clockwork/wiki).

## Support & Contributing

- **Issue Tracker**: [GitHub Issues](https://github.com/mutilator/clockwork/issues)
- **License**: MIT License - See [LICENSE](LICENSE) for details

## Credits

Clockwork is built to integrate seamlessly with Home Assistant and follows all Home Assistant custom component standards.

---

**Ready to get started?** Head over to the [wiki](https://github.com/mutilator/clockwork/wiki) for detailed guides and examples!
