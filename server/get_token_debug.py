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
    user_id = "114738fa7a15ca2374cc5fd97515d93d"
    email = "parth.ajit7052@gmail.com"
    
    token = create_access_token(
        data={"sub": email, "id": user_id},
        expires_delta=timedelta(days=1)
    )
    print(token)
