import asyncio
import jwt
from datetime import datetime, timedelta, timezone
from config import SECRET_KEY

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=60)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm="HS256")
    return encoded_jwt

if __name__ == "__main__":
    # Use the secret from heroku config
    ACTUAL_JWT_SECRET = "72b2b66ab650740858e1409283fb365d7ac0546e240076f21a9d32a1669a6327" # pragma: allowlist secret
    user_id = "114738fa7a15ca2374cc5fd97515d93d"
    email = "parth.ajit7052@gmail.com"
    
    # Payload must have 'sub' as user_id because get_current_user uses payload["sub"]
    token = jwt.encode({
        "sub": user_id,
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(days=1)
    }, ACTUAL_JWT_SECRET, algorithm="HS256")
    
    print(token)
