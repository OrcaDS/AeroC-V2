# AeroC dashboard

React + TypeScript implementation of the AeroC monitoring product.

## Run locally

1. Start the backend at `http://localhost:8000`.
2. From this directory, run `npm.cmd run dev`.
3. Open the Vite URL shown in the terminal.

The development server proxies `/api` requests to the backend. For another API
origin, set `VITE_API_URL`, including the `/api/v1` path.

## Product contracts

The dashboard renders the existing AeroC API only. It does not calculate AQI,
infer data freshness, add health advisories, or invent collection schedules.
AQI is displayed as an estimated provider-model snapshot with the limitations
returned by the backend.
