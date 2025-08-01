def test_auth_routes_defined():
    """Simple test to verify auth routes are properly defined"""
    # This test just verifies the auth router file can be imported
    try:
        from backend.routers import auth
        assert hasattr(auth, 'router')
        assert auth.router is not None
        print("✓ Auth router imported successfully")
    except Exception as e:
        print(f"✗ Auth router import failed: {e}")
        raise

def test_auth_router_has_signup():
    """Test that signup route is defined"""
    from backend.routers import auth
    routes = [route.path for route in auth.router.routes]
    assert "/signup" in routes
    print("✓ Signup route found")

def test_auth_router_has_login():
    """Test that login route is defined"""
    from backend.routers import auth
    routes = [route.path for route in auth.router.routes]
    assert "/login" in routes
    print("✓ Login route found") 