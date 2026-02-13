import jwt
import datetime
import os

SECRET_KEY = os.environ["JWT_SECRET"]
ALGORITHM = "HS256"

def create_access_token(data: dict, valid_for_hours: float):
    expires_delta = datetime.timedelta(hours=valid_for_hours)
    to_encode = data.copy()
    expire = datetime.datetime.now(tz=datetime.timezone.utc) + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str):
    try:
        decoded_token = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return decoded_token
    except jwt.ExpiredSignatureError:
        return None # Token has expired
    except jwt.InvalidTokenError:
        return None # Invalid token
    


from passlib.context import CryptContext

# Define a CryptContext with bcrypt as the default scheme
# "auto" deprecation means all schemes except the default are marked as deprecated
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    """Verifies a plain-text password against a stored hash."""
    # The verify() method uses a constant-time comparison to prevent timing attacks
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    """Generates a secure hash for a plain-text password."""
    # hash() automatically generates a new salt each time it's called
    return pwd_context.hash(password)

# Example usage:
password = "mysecretpassword"
hashed = get_password_hash(password)
print(f"Hashed password: {hashed}")

# Verify a correct password
is_correct = verify_password(password, hashed)
print(f"Password verification result (correct): {is_correct}")

# Verify an incorrect password
is_incorrect = verify_password("wrongpassword", hashed)
print(f"Password verification result (incorrect): {is_incorrect}")