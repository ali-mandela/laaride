# Test Payments Module

# Prerequisites:
# 1. Start the server
# 2. Login as passenger and driver (get JWT tokens)
# 3. Create a booking and CONFIRM it by driver

PASSENGER_TOKEN="your_passenger_jwt"
DRIVER_TOKEN="your_driver_jwt"
ADMIN_TOKEN="your_admin_jwt"
BASE_URL="http://localhost:8000/api/v1"
BOOKING_ID="your_confirmed_booking_id"

# 1. Initiate cash payment (Passenger)
curl -X POST "$BASE_URL/payments/initiate" \
     -H "Authorization: Bearer $PASSENGER_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "booking_id": "'$BOOKING_ID'",
       "payment_method": "cash"
     }'

# 2. Driver confirms cash received
curl -X POST "$BASE_URL/payments/cash-confirm" \
     -H "Authorization: Bearer $DRIVER_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "booking_id": "'$BOOKING_ID'"
     }'

# 3. Get payment for booking (Passenger/Driver/Admin)
curl -X GET "$BASE_URL/payments/booking/$BOOKING_ID" \
     -H "Authorization: Bearer $PASSENGER_TOKEN"

# 4. Get payment stats (Admin)
curl -X GET "$BASE_URL/payments/stats" \
     -H "Authorization: Bearer $ADMIN_TOKEN"

# 5. Initiate Online Payment (Passenger)
# Note: This will return a razorpay_order_id. You'd normally use the frontend SDK to complete it.
curl -X POST "$BASE_URL/payments/initiate" \
     -H "Authorization: Bearer $PASSENGER_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "booking_id": "'$BOOKING_ID'",
       "payment_method": "online"
     }'
