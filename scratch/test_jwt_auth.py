import sys
import json
import shutil
import pandas as pd
from pathlib import Path

# Add workspace directory to python path
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from backend.app.db.session import SessionLocal
from backend.app.db.models import User, RefreshToken

def main():
    print("==================================================")
    print("Testing JWT Refresh Token Rotation & Profile...")
    print("==================================================")
    
    base_url = "http://localhost:8000"
    
    # 1. Register a test user via python or direct API (using a clean username)
    test_username = "test_user_jwt"
    test_email = "test_user_jwt@example.com"
    test_password = "test_password_123"
    
    db = SessionLocal()
    try:
        # Delete user if already exists to ensure clean run
        db.query(User).filter(User.username == test_username).delete()
        db.commit()
        
        # We start the backend server to test actual API calls.
        # But wait! Can we test it directly via FastAPI TestClient to make it easier and not require a running server?
        # Yes! FastAPI's TestClient is perfect for testing FastAPI applications.
        from fastapi.testclient import TestClient
        from backend.app.main import app
        
        client = TestClient(app)
        
        # 1. Register user
        print("Registering user...")
        resp = client.post("/api/auth/register", json={
            "email": test_email,
            "username": test_username,
            "password": test_password
        })
        print(f"  Register Response Status: {resp.status_code}")
        assert resp.status_code == 200, "Registration failed"
        
        # 2. Login
        print("Logging in to obtain tokens...")
        resp = client.post("/api/auth/token", data={
            "username": test_username,
            "password": test_password
        })
        print(f"  Login Response Status: {resp.status_code}")
        assert resp.status_code == 200, "Login failed"
        login_data = resp.json()
        access_token = login_data["access_token"]
        
        # Read the refresh token cookie from the client's cookies
        refresh_token_cookie = client.cookies.get("refresh_token")
        print(f"  Received Refresh Token Cookie: {refresh_token_cookie is not None}")
        assert refresh_token_cookie is not None, "Refresh token cookie missing"
        
        # 3. Retrieve profile using access token
        print("Retrieving user profile using access token...")
        headers = {"Authorization": f"Bearer {access_token}"}
        resp = client.get("/api/auth/me", headers=headers)
        print(f"  Profile Response Status: {resp.status_code}")
        assert resp.status_code == 200, "Me profile call failed"
        profile_data = resp.json()
        assert profile_data["username"] == test_username, "Profile username mismatch"
        print(f"  Profile retrieved: {profile_data['username']}")
        
        # 4. Refresh token rotation
        print("Refreshing token (Cookie-based rotation)...")
        # TestClient handles cookies automatically
        resp = client.post("/api/auth/refresh")
        print(f"  Refresh Response Status: {resp.status_code}")
        assert resp.status_code == 200, "Refresh call failed"
        refresh_data = resp.json()
        new_access_token = refresh_data["access_token"]
        
        new_refresh_token_cookie = client.cookies.get("refresh_token")
        assert new_refresh_token_cookie is not None, "New refresh token cookie missing"
        assert new_refresh_token_cookie != refresh_token_cookie, "Refresh token was not rotated (same value)"
        print("  [OK] Refresh token rotated successfully.")
        
        # 5. Check in DB if old token is revoked
        import hashlib
        old_hash = hashlib.sha256(refresh_token_cookie.encode()).hexdigest()
        old_db_token = db.query(RefreshToken).filter(RefreshToken.token_hash == old_hash).first()
        print(f"  Old Refresh Token in DB is revoked: {old_db_token.revoked if old_db_token else 'Not found'}")
        assert old_db_token is not None, "Old refresh token not found in DB"
        assert old_db_token.revoked, "Old refresh token was not marked revoked in the database"
        
        # 6. Check that reusing the old refresh token fails and revokes everything
        print("Testing refresh token reuse detection...")
        # Manually clear the cookies and set the old one
        reuse_client = TestClient(app)
        reuse_client.cookies.set("refresh_token", refresh_token_cookie)
        resp = reuse_client.post("/api/auth/refresh")
        print(f"  Reuse Response Status (Expected: 401): {resp.status_code}")
        assert resp.status_code == 401, "Reusing old refresh token should have failed"
        
        # Check that the new refresh token is also revoked due to reuse detection
        new_hash = hashlib.sha256(new_refresh_token_cookie.encode()).hexdigest()
        new_db_token = db.query(RefreshToken).filter(RefreshToken.token_hash == new_hash).first()
        print(f"  New Refresh Token in DB is revoked due to reuse: {new_db_token.revoked if new_db_token else 'Not found'}")
        assert new_db_token is not None, "New refresh token not found in DB"
        assert new_db_token.revoked, "New refresh token should be revoked after old token reuse detection"
        
        # 7. Logout
        print("Logging out...")
        logout_client = TestClient(app)
        logout_client.cookies.set("refresh_token", new_refresh_token_cookie)
        resp = logout_client.post("/api/auth/logout")
        print(f"  Logout Response Status: {resp.status_code}")
        assert resp.status_code == 200, "Logout failed"
        
        print("\n==================================================")
        print("SUCCESS: JWT Refresh Token Rotation verification passed!")
        print("==================================================")
        
    except Exception as e:
        print(f"  [ERROR] Test failed with error: {e}")
        sys.exit(1)
    finally:
        # Clean up database test user and tokens
        test_user = db.query(User).filter(User.username == test_username).first()
        if test_user:
            db.query(RefreshToken).filter(RefreshToken.user_id == test_user.id).delete()
            db.delete(test_user)
            db.commit()
            print("  [OK] Cleaned up test user and refresh tokens from DB.")
        db.close()

if __name__ == "__main__":
    main()
