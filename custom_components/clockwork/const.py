"""Constants for Clockwork integration."""
DOMAIN = "clockwork"

CONF_CALCULATIONS = "calculations"

# Calculation types
CALC_TYPE_TIMESPAN = "timespan"
CALC_TYPE_OFFSET = "offset"
CALC_TYPE_DATETIME_OFFSET = "datetime_offset"
CALC_TYPE_SEASON = "season"
CALC_TYPE_MONTH = "month"
CALC_TYPE_HOLIDAY = "holiday"
CALC_TYPE_EVENT_OFFSET = "event_offset"
CALC_TYPE_BETWEEN_DATES = "between_dates"
CALC_TYPE_OUTSIDE_DATES = "outside_dates"
CALC_TYPE_DATE_RANGE = "date_range"

# Platforms
PLATFORMS = ["sensor", "binary_sensor"]