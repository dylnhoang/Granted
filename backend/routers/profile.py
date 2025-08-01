from fastapi import APIRouter, Depends, HTTPException, Header, Body, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase import create_client
import os
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
router = APIRouter()

security = HTTPBearer()

class UserProfile(BaseModel):
    user_id: str
    major: str
    gpa: float
    state: str
    interests: list[str]

class CreateProfileRequest(BaseModel):
    full_name: str

def get_user_from_token(token: str):
    try:
        # Remove 'Bearer ' prefix if present
        if token.startswith('Bearer '):
            token = token[7:]
        
        # Get user from Supabase
        user_response = supabase.auth.get_user(token)
        
        if not user_response or not user_response.user:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        return user_response.user
    except Exception as e:
        print(f"Token validation error: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid or missing token")
    
@router.get("/test-auth")
def test_auth():
    """Test endpoint to verify Supabase connection"""
    try:
        # Test if Supabase URL and key are set
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        
        if not supabase_url or not supabase_key:
            return {
                "error": "Missing Supabase environment variables",
                "url_set": bool(supabase_url),
                "key_set": bool(supabase_key),
                "help": "Create a .env file with SUPABASE_URL and SUPABASE_KEY"
            }
        
        return {
            "message": "Supabase connection configured",
            "url_set": bool(supabase_url),
            "key_set": bool(supabase_key),
            "url_preview": supabase_url[:30] + "..." if supabase_url else None
        }
    except Exception as e:
        return {"error": f"Connection test failed: {str(e)}"}

@router.get("/health")
def health_check():
    """Simple health check endpoint"""
    return {
        "status": "healthy",
        "message": "API is running",
        "endpoints": {
            "test_auth": "/test-auth",
            "debug_token": "/debug-token",
            "me": "/me (requires auth)",
            "docs": "/docs"
        }
    }

@router.get("/debug-token")
def debug_token(authorization: str = Header(None)):
    """Debug endpoint to test token parsing"""
    if not authorization:
        return {"error": "No authorization header provided"}
    
    if not authorization.startswith("Bearer "):
        return {"error": "Authorization header must start with 'Bearer '"}
    
    token = authorization[7:]  # Remove "Bearer " prefix
    
    # Try to validate the token with Supabase
    try:
        user_response = supabase.auth.get_user(token)
        if user_response and user_response.user:
            return {
                "message": "Token is valid",
                "token_length": len(token),
                "token_preview": token[:20] + "..." if len(token) > 20 else token,
                "starts_with_ey": token.startswith("ey"),
                "user_id": user_response.user.id,
                "user_email": user_response.user.email
            }
        else:
            return {
                "message": "Token validation failed",
                "token_length": len(token),
                "token_preview": token[:20] + "..." if len(token) > 20 else token,
                "starts_with_ey": token.startswith("ey"),
                "error": "No user found in response"
            }
    except Exception as e:
        return {
            "message": "Token validation error",
            "token_length": len(token),
            "token_preview": token[:20] + "..." if len(token) > 20 else token,
            "starts_with_ey": token.startswith("ey"),
            "error": str(e)
        }

@router.get("/me")
def get_profile(credentials: HTTPAuthorizationCredentials = Security(security)):
    try:
        token = credentials.credentials
        print(f"Received token: {token[:20]}...")  # Debug: print first 20 chars
        
        user = get_user_from_token(token)
        user_id = user.id  # Access the id attribute directly
        
        print(f"User ID: {user_id}")  # Debug: print user ID
        
        # Query profile from Supabase - use limit(1) instead of single() to avoid PGRST116 error
        res = supabase.table("profiles").select("*").eq("id", user_id).limit(1).execute()

        if res.data and len(res.data) > 0:
            return res.data[0]  # Return the first (and only) profile
        else:
            # Return empty profile if not found
            return {
                "id": user_id,
                "message": "Profile not found, please create one",
                "user_email": user.email
            }
    except Exception as e:
        print(f"Error in /me endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/me-test")
def get_profile_test():
    """Temporary test endpoint without authentication"""
    try:
        # Test if we can query the profiles table
        res = supabase.table("profiles").select("*").limit(5).execute()
        
        return {
            "message": "Database connection test",
            "profiles_count": len(res.data) if res.data else 0,
            "sample_profiles": res.data[:2] if res.data else []
        }
    except Exception as e:
        return {"error": f"Database test failed: {str(e)}"}

@router.post("/create-profile")
def create_profile(authorization: str = Header(...), request: CreateProfileRequest = Body(...)):
    """Create a new profile for the authenticated user"""
    try:
        token = authorization.split("Bearer ")[-1]
        user = get_user_from_token(token)
        user_id = user.id
        
        # Create profile
        profile_data = {
            "id": user_id,
            "full_name": request.full_name
        }
        
        res = supabase.table("profiles").upsert(profile_data).execute()
        
        return {
            "message": "Profile created successfully",
            "profile": res.data[0] if res.data else profile_data
        }
    except Exception as e:
        print(f"Error creating profile: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create profile: {str(e)}")
    
@router.post("/profile/update")
def update_profile(full_name: str = Body(...), authorization: str = Header(...)):
    token = authorization.split("Bearer ")[-1]
    user = get_user_from_token(token)
    user_id = user.id  # Use .id attribute consistently

    res = supabase.table("profiles").upsert({
        "id": user_id,
        "full_name": full_name,
    }).execute()

    return {"message": "Profile updated", "profile": res.data}

@router.post("/profile")
def save_profile(profile: UserProfile, authorization: str = Header(...)):
    token = authorization.split("Bearer ")[-1]
    user = get_user_from_token(token)
    user_id = user.id  # Use .id attribute consistently

    # enforce that only the current user can write their own profile
    if user_id != profile.user_id:
        raise HTTPException(status_code=403, detail="Cannot modify another user's profile")

    response = supabase.table("profiles").upsert(profile.dict()).execute()
    return {"status": "success", "data": response.data}
