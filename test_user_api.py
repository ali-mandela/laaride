import httpx
import time
import os
import json

BASE_URL = "http://localhost:8000/api/v1"
PHONE = "+919876543210"

def log_step(title):
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")

def test_user_module():
    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        # Step 1: Send OTP
        log_step("STEP 1: Send OTP")
        resp = client.post("/auth/send-otp", json={"phone": PHONE})
        print(f"Status: {resp.status_code}")
        data = resp.json()
        print(json.dumps(data, indent=2))
        
        # In development mode, the OTP is returned in the response
        otp_code = data.get("otp")
        if not otp_code:
            otp_code = input("\nEnter OTP (if not in dev mode): ")
        else:
            print(f"\nAuto-detected OTP: {otp_code}")

        # Step 2: Verify OTP
        log_step("STEP 2: Verify OTP")
        resp = client.post("/auth/verify-otp", json={"phone": PHONE, "otp": otp_code})
        print(f"Status: {resp.status_code}")
        verify_data = resp.json()
        print(json.dumps(verify_data, indent=2))
        
        token = verify_data.get("access_token")
        if not token:
            print("Failed to get token. Exiting.")
            return

        headers = {"Authorization": f"Bearer {token}"}

        # TEST 1: GET /users/me
        log_step("TEST 1: GET /users/me")
        resp = client.get("/users/me", headers=headers)
        print(f"Status: {resp.status_code}")
        print(json.dumps(resp.json(), indent=2))

        # TEST 2: PUT /users/me
        log_step("TEST 2: PUT /users/me")
        resp = client.put("/users/me", headers=headers, json={
            "name": "Rahul Sharma",
            "email": "rahul@example.com"
        })
        print(f"Status: {resp.status_code}")
        print(json.dumps(resp.json(), indent=2))

        # TEST 3: POST /users/me/photo
        log_step("TEST 3: POST /users/me/photo")
        # Create a dummy image
        with open("test_photo.jpg", "wb") as f:
            f.write(b"fake image data")
        
        with open("test_photo.jpg", "rb") as f:
            files = {"file": ("test_photo.jpg", f, "image/jpeg")}
            resp = client.post("/users/me/photo", headers=headers, files=files)
        
        os.remove("test_photo.jpg")
        print(f"Status: {resp.status_code}")
        print(json.dumps(resp.json(), indent=2))

        # TEST 4: GET /users/me/bookings
        log_step("TEST 4: GET /users/me/bookings")
        resp = client.get("/users/me/bookings", params={"skip": 0, "limit": 10}, headers=headers)
        print(f"Status: {resp.status_code}")
        print(json.dumps(resp.json(), indent=2))

        # TEST 5: GET /users (Admin)
        log_step("TEST 5: GET /users (Admin only)")
        resp = client.get("/users/", params={"skip": 0, "limit": 10}, headers=headers)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 403:
            print("Access Forbidden (User is not an admin)")
        else:
            print(json.dumps(resp.json(), indent=2))

        # TEST 6: DELETE /users/me (Deactivate)
        log_step("TEST 6: DELETE /users/me (Deactivate)")
        resp = client.delete("/users/me", headers=headers)
        print(f"Status: {resp.status_code}")
        print(json.dumps(resp.json(), indent=2))

if __name__ == "__main__":
    try:
        test_user_module()
    except httpx.ConnectError:
        print("\nError: Could not connect to the server. Is it running on http://localhost:8000?")
    except Exception as e:
        print(f"\nAn error occurred: {e}")
