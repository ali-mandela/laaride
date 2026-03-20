@echo off
REM ═══════════════════════════════════════════════════════════════
REM  LaaRide User API Test Script
REM  Run the server first: uv run python run.py
REM  Then run this script in a separate terminal.
REM ═══════════════════════════════════════════════════════════════

set BASE=http://localhost:8000/api/v1
set PHONE=+919876543210

echo.
echo ══════════════════════════════════════════════════════
echo  STEP 1: Send OTP
echo ══════════════════════════════════════════════════════
curl -s -X POST %BASE%/auth/send-otp -H "Content-Type: application/json" -d "{\"phone\": \"%PHONE%\"}"
echo.

echo.
echo ══════════════════════════════════════════════════════
echo  STEP 2: Verify OTP (replace OTP_CODE with actual OTP from step 1)
echo  Copy the "otp" value from above and paste below
echo ══════════════════════════════════════════════════════
set /p OTP_CODE="Enter OTP: "
echo.

REM Capture the token from verify-otp response
echo Verifying OTP...
curl -s -X POST %BASE%/auth/verify-otp -H "Content-Type: application/json" -d "{\"phone\": \"%PHONE%\", \"otp\": \"%OTP_CODE%\"}"
echo.
echo.
set /p TOKEN="Copy the access_token from above and paste here: "
echo.

echo ══════════════════════════════════════════════════════
echo  TEST 1: GET /users/me — Get current user profile
echo ══════════════════════════════════════════════════════
curl -s -X GET %BASE%/users/me -H "Authorization: Bearer %TOKEN%"
echo.
echo.

echo ══════════════════════════════════════════════════════
echo  TEST 2: PUT /users/me — Update name and email
echo ══════════════════════════════════════════════════════
curl -s -X PUT %BASE%/users/me -H "Authorization: Bearer %TOKEN%" -H "Content-Type: application/json" -d "{\"name\": \"Rahul Sharma\", \"email\": \"rahul@example.com\"}"
echo.
echo.

echo ══════════════════════════════════════════════════════
echo  TEST 3: POST /users/me/photo — Upload profile photo
echo  (Creates a tiny test image first)
echo ══════════════════════════════════════════════════════
echo test > test_photo.jpg
curl -s -X POST %BASE%/users/me/photo -H "Authorization: Bearer %TOKEN%" -F "file=@test_photo.jpg"
del test_photo.jpg 2>nul
echo.
echo.

echo ══════════════════════════════════════════════════════
echo  TEST 4: GET /users/me/bookings — Get booking history
echo ══════════════════════════════════════════════════════
curl -s -X GET "%BASE%/users/me/bookings?skip=0&limit=10" -H "Authorization: Bearer %TOKEN%"
echo.
echo.

echo ══════════════════════════════════════════════════════
echo  TEST 5: DELETE /users/me — Deactivate account
echo ══════════════════════════════════════════════════════
curl -s -X DELETE %BASE%/users/me -H "Authorization: Bearer %TOKEN%"
echo.
echo.

echo ══════════════════════════════════════════════════════
echo  TEST 6: GET /users — List all users (admin only)
echo  (Will return 403 if current user is not admin)
echo ══════════════════════════════════════════════════════
curl -s -X GET "%BASE%/users/?skip=0&limit=10" -H "Authorization: Bearer %TOKEN%"
echo.
echo.

echo ══════════════════════════════════════════════════════
echo  TEST 7: GET /users/{user_id} — Get user by ID (admin)
echo  (Replace USER_ID with an actual user _id from your DB)
echo ══════════════════════════════════════════════════════
set /p USER_ID="Enter a user_id to fetch (or press Enter to skip): "
if not "%USER_ID%"=="" (
    curl -s -X GET %BASE%/users/%USER_ID% -H "Authorization: Bearer %TOKEN%"
    echo.
)
echo.

echo ══════════════════════════════════════════════════════
echo  TEST 8: PUT /users/{user_id} — Update user (admin)
echo ══════════════════════════════════════════════════════
if not "%USER_ID%"=="" (
    curl -s -X PUT %BASE%/users/%USER_ID% -H "Authorization: Bearer %TOKEN%" -H "Content-Type: application/json" -d "{\"name\": \"Admin Updated Name\"}"
    echo.
)
echo.

echo.
echo ══════════════════════════════════════════════════════
echo  ALL TESTS COMPLETE
echo ══════════════════════════════════════════════════════
pause
