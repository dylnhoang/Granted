from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from backend.routers import profile, match_grants, auth

app = FastAPI()

app.include_router(profile.router)
app.include_router(match_grants.router)
app.include_router(auth.router)

@app.get("/")
def read_root():
    return {"message": "Granted API is running!"}

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="Granted API",
        version="1.0.0",
        description="API for Granted",
        routes=app.routes,
    )
    
    # Initialize components if it doesn't exist
    if "components" not in openapi_schema:
        openapi_schema["components"] = {}
    
    openapi_schema["components"]["securitySchemes"] = {
        "bearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }
    
    # Only add security to paths if paths exist
    if "paths" in openapi_schema:
        for path in openapi_schema["paths"]:
            for method in openapi_schema["paths"][path]:
                if isinstance(openapi_schema["paths"][path][method], dict):
                    openapi_schema["paths"][path][method]["security"] = [{"bearerAuth": []}]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi