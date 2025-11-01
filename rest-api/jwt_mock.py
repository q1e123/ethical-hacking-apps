from fastapi import Request
#MOCK JWT 
def get_user_id(request: Request):
    token = request.headers.get("Authorization", "")
    # Normally decode JWT, here just mock
    return token.replace("Bearer ", "") or "anonymous"