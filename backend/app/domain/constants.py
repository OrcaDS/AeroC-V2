"""
Application-wide constants.

These values are shared across collectors, services, and other
components to ensure consistent behavior throughout AeroC.
"""

SUPPORTED_POLLUTANTS = (
    "pm2_5",
    "pm10",
    "carbon_monoxide",
    "nitrogen_dioxide",
    "sulphur_dioxide",
    "ozone",
)

DATA_SOURCE_OPEN_METEO = "open-meteo"

HTTP_TIMEOUT_SECONDS = 30.0