# City of Casey Waste Collection API

A Flask-based REST API that provides waste collection information for addresses in the City of Casey, Victoria.

## Installation

1. Install dependencies:
```bash
pip3 install -r requirements.txt
```

## Running the API

Start the API server:
```bash
python3 api.py
```

The API will be available at `http://localhost:5000`

## API Endpoints

### POST /api/waste-collection

Get waste collection information for a specific address.

**Request Body:**
```json
{
  "address": "2 Patrick Northeast Drive, Narre Warren, VIC"
}
```

**Success Response (200):**
```json
{
  "address": "2 Patrick Northeast Drive, Narre Warren, VIC",
  "postcode": "3805",
  "collection_day": "Monday",
  "collection_week": "2",
  "current_week": 2,
  "is_collection_week": true,
  "night_before": "Sunday",
  "bins_this_week": [
    "Rubbish (red lid)",
    "Recycling (yellow lid)"
  ],
  "bins_next_week": [
    "Rubbish (red lid)",
    "Food & Garden (green lid)"
  ]
}
```

**Error Response (400):**
```json
{
  "error": "Address not found. Please check the address and try again."
}
```

### GET /api/health

Health check endpoint.

**Response:**
```json
{
  "status": "ok",
  "service": "City of Casey Waste Collection API"
}
```

### GET /

API documentation endpoint showing available endpoints.

## Usage Examples

### Using curl:

```bash
curl -X POST http://localhost:5000/api/waste-collection \
  -H "Content-Type: application/json" \
  -d '{"address": "2 Patrick Northeast Drive, Narre Warren, VIC"}'
```

### Using Python requests:

```python
import requests

url = "http://localhost:5000/api/waste-collection"
data = {"address": "2 Patrick Northeast Drive, Narre Warren, VIC"}

response = requests.post(url, json=data)
result = response.json()

if response.status_code == 200:
    print(f"Collection Day: {result['collection_day']}")
    print(f"Bins this week: {', '.join(result['bins_this_week'])}")
else:
    print(f"Error: {result['error']}")
```

### Using JavaScript fetch:

```javascript
fetch('http://localhost:5000/api/waste-collection', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    address: '2 Patrick Northeast Drive, Narre Warren, VIC'
  })
})
  .then(response => response.json())
  .then(data => {
    if (data.error) {
      console.error('Error:', data.error);
    } else {
      console.log('Collection Day:', data.collection_day);
      console.log('Bins this week:', data.bins_this_week);
    }
  });
```

## Response Fields

- `address`: The queried address
- `postcode`: Australian postcode for the address
- `collection_day`: Day of the week for waste collection (e.g., "Monday")
- `collection_week`: The week pattern for this area ("1" or "2")
- `current_week`: The current week in the fortnightly cycle ("1" or "2")
- `is_collection_week`: Boolean indicating if this is the collection week for this address
- `night_before`: The night before collection (when to put bins out)
- `bins_this_week`: Array of bin types to put out this week
- `bins_next_week`: Array of bin types for next collection

## Error Handling

The API returns appropriate HTTP status codes:
- `200`: Success
- `400`: Bad request (missing address, address not found, or other errors)
- `500`: Server error

All error responses include an `error` field with a descriptive message.

## CORS

CORS is enabled for all routes, allowing the API to be called from web applications.

## Production Deployment

For production deployment, consider:
- Using a production WSGI server like Gunicorn or uWSGI
- Setting up proper logging
- Adding rate limiting
- Using environment variables for configuration
- Disabling debug mode

Example with Gunicorn:
```bash
pip3 install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 api:app
```
