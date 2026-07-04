"""
Official monitoring network for AeroC.

This module defines the cities monitored by the platform.
It serves as the single source of truth for seed data.
"""

CITIES = [
    # Philippines
    {
        "code": "PH-MNL",
        "name": "Manila",
        "country": "Philippines",
        "latitude": 14.5995,
        "longitude": 120.9842,
        "timezone": "Asia/Manila",
    },
    {
        "code": "PH-QC",
        "name": "Quezon City",
        "country": "Philippines",
        "latitude": 14.6760,
        "longitude": 121.0437,
        "timezone": "Asia/Manila",
    },
    {
        "code": "PH-MKT",
        "name": "Makati",
        "country": "Philippines",
        "latitude": 14.5547,
        "longitude": 121.0244,
        "timezone": "Asia/Manila",
    },
    {
        "code": "PH-TAG",
        "name": "Taguig",
        "country": "Philippines",
        "latitude": 14.5176,
        "longitude": 121.0509,
        "timezone": "Asia/Manila",
    },
    {
        "code": "PH-PAS",
        "name": "Pasig",
        "country": "Philippines",
        "latitude": 14.5764,
        "longitude": 121.0851,
        "timezone": "Asia/Manila",
    },

    # Indonesia
    {
        "code": "ID-JKT",
        "name": "Jakarta",
        "country": "Indonesia",
        "latitude": -6.2088,
        "longitude": 106.8456,
        "timezone": "Asia/Jakarta",
    },
    {
        "code": "ID-SBY",
        "name": "Surabaya",
        "country": "Indonesia",
        "latitude": -7.2504,
        "longitude": 112.7688,
        "timezone": "Asia/Jakarta",
    },
    {
        "code": "ID-BDG",
        "name": "Bandung",
        "country": "Indonesia",
        "latitude": -6.9175,
        "longitude": 107.6191,
        "timezone": "Asia/Jakarta",
    },
]