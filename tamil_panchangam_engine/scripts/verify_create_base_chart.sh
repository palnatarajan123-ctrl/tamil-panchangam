#!/bin/bash

echo "🚀 Creating base chart..."

curl -s -X POST http://localhost:8001/api/base-chart/create \
  -H "Content-Type: application/json" \
  -d '{
    "name": "EPIC-6 DB Test",
    "date_of_birth": "1978-01-01",
    "time_of_birth": "01:01:01",
    "place_of_birth": "Chennai",
    "latitude": 13.0837,
    "longitude": 80.2707,
    "timezone": "Asia/Kolkata"
  }' | tee /tmp/base_chart_response.json

echo ""
echo "✅ API response saved to /tmp/base_chart_response.json"
