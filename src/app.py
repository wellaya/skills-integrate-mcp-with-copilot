"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import secrets

from fastapi import Cookie, Depends, FastAPI, HTTPException, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
import os
from pathlib import Path

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

SESSION_TTL = timedelta(hours=8)
session_tokens = {}
password_hashes = {}
bearer_scheme = HTTPBearer(auto_error=False)


class LoginRequest(BaseModel):
    email: str
    password: str


class ActivityRequest(BaseModel):
    name: str = Field(min_length=1)
    description: str
    schedule: str
    max_participants: int = Field(gt=0)


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 120_000)
    return f"{salt.hex()}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    salt_hex, digest_hex = stored_hash.split("$", 1)
    expected = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), bytes.fromhex(salt_hex), 120_000
    )
    return hmac.compare_digest(expected.hex(), digest_hex)


def add_user(email: str, role: str, password: str) -> None:
    password_hashes[email] = {
        "role": role,
        "password": hash_password(password),
    }


add_user("teacher@mergington.edu", "teacher", "teacher123")
add_user("student@mergington.edu", "student", "student123")


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session_cookie: str | None = Cookie(default=None, alias="mergington_session"),
):
    token = credentials.credentials if credentials else session_cookie
    session = session_tokens.get(token)
    if not session or session["expires_at"] <= datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Authentication required")
    return session["user"]


def require_teacher(user=Depends(get_current_user)):
    if user["role"] != "teacher":
        raise HTTPException(status_code=403, detail="Teacher access required")
    return user

# In-memory activity database
activities = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    }
}


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.post("/auth/login")
def login(login_request: LoginRequest, response: Response):
    email = login_request.email.strip().lower()
    user = password_hashes.get(email)
    if not user or not verify_password(login_request.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = secrets.token_urlsafe(32)
    session_tokens[token] = {
        "user": {"email": email, "role": user["role"]},
        "expires_at": datetime.now(timezone.utc) + SESSION_TTL,
    }
    response.set_cookie(
        "mergington_session",
        token,
        max_age=int(SESSION_TTL.total_seconds()),
        httponly=True,
        samesite="lax",
    )
    return session_tokens[token]["user"]


@app.post("/auth/logout")
def logout(response: Response, session_cookie: str | None = Cookie(default=None, alias="mergington_session")):
    if session_cookie:
        session_tokens.pop(session_cookie, None)
    response.delete_cookie("mergington_session")
    return {"message": "Logged out"}


@app.get("/auth/me")
def current_user(user=Depends(get_current_user)):
    return user


@app.get("/activities")
def get_activities():
    return activities


@app.post("/activities", status_code=201)
def create_activity(activity_request: ActivityRequest, user=Depends(require_teacher)):
    activity_name = activity_request.name.strip()
    if not activity_name or activity_name in activities:
        raise HTTPException(status_code=400, detail="Activity name must be unique")
    activities[activity_name] = {
        "description": activity_request.description,
        "schedule": activity_request.schedule,
        "max_participants": activity_request.max_participants,
        "participants": [],
    }
    return activities[activity_name]


@app.put("/activities/{activity_name}")
def update_activity(
    activity_name: str,
    activity_request: ActivityRequest,
    user=Depends(require_teacher),
):
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")
    if activity_request.max_participants < len(activities[activity_name]["participants"]):
        raise HTTPException(
            status_code=400,
            detail="Capacity cannot be lower than current enrollment",
        )
    activities[activity_name].update({
        "description": activity_request.description,
        "schedule": activity_request.schedule,
        "max_participants": activity_request.max_participants,
    })
    return activities[activity_name]


@app.delete("/activities/{activity_name}")
def delete_activity(activity_name: str, user=Depends(require_teacher)):
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")
    del activities[activity_name]
    return {"message": f"Deleted {activity_name}"}


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str, user=Depends(get_current_user)):
    """Sign up a student for an activity"""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    email = email.strip().lower()
    if user["role"] != "teacher" and user["email"] != email:
        raise HTTPException(status_code=403, detail="Students can only manage their own registration")

    # Get the specific activity
    activity = activities[activity_name]

    if len(activity["participants"]) >= activity["max_participants"]:
        raise HTTPException(status_code=409, detail="Activity is full")

    # Validate student is not already signed up
    if email in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is already signed up"
        )

    # Add student
    activity["participants"].append(email)
    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, email: str, user=Depends(get_current_user)):
    """Unregister a student from an activity"""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    email = email.strip().lower()
    if user["role"] != "teacher" and user["email"] != email:
        raise HTTPException(status_code=403, detail="Students can only manage their own registration")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is signed up
    if email not in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is not signed up for this activity"
        )

    # Remove student
    activity["participants"].remove(email)
    return {"message": f"Unregistered {email} from {activity_name}"}
