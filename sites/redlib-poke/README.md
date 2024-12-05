# redlib-poke

A simple URL monitoring tool designed specifically to handle intermittent timeouts with [redlib](https://github.com/redlib-org/redlib) instances, particularly when running via Coolify.

## Problem

When running redlib through Coolify, initial page loads sometimes timeout. This tool acts as a middleground that continuously polls the redlib instance until it receives a fast response, indicating that the page is properly loaded and ready to serve content.

## How it Works

1. Add your redlib URL as a query parameter: `?url=YOUR_REDLIB_URL`
2. The tool will:
   - Continuously poll the specified URL every 5 seconds
   - Monitor response times
   - Automatically redirect to the redlib instance once a fast response (< 2000ms) is detected
   - Display current request count and last response time

## Usage

Simply append your redlib URL to this tool's address:

```
https://your-redlib-poke-instance/?url=https://your-redlib-instance
```

## Configuration

The tool uses the following default settings:
- Expected response time threshold: 2000ms
- Request timeout: 5000ms
- Polling interval: 5000ms (5 seconds)

## Technical Details

Built with:
- Vue.js 3
- Tailwind CSS
