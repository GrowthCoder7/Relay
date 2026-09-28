from supabase import create_client, Client
from dotenv import load_dotenv
import os

load_dotenv()

def get_client() -> Client:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    return create_client(url, key)

def create_session(task: str, participant_name: str = "Anonymous") -> dict:
    client = get_client()
    result = client.table("sessions").insert({"task": task, "status": "running", "owner_id": participant_name}).execute()
    return result.data[0] if result.data else {}

def add_step(session_id: str, step_number: int, step_type: str, content: str, author: str = "agent") -> dict:
    client = get_client()
    result = client.table("steps").insert({
        "session_id": session_id,
        "step_number": step_number,
        "step_type": step_type,
        "content": content,
        "author": author
    }).execute()
    return result.data[0] if result.data else {}

def get_session(session_id: str) -> dict:
    client = get_client()
    result = client.table("sessions").select("*").eq("id", session_id).single().execute()
    return result.data if result.data else {}

def get_steps(session_id: str) -> list[dict]:
    client = get_client()
    result = client.table("steps").select("*").eq("session_id", session_id).order("step_number", desc=False).execute()
    return result.data if result.data else []

def list_sessions() -> list[dict]:
    client = get_client()
    result = client.table("sessions").select("*").order("created_at", desc=True).execute()
    return result.data if result.data else []

def update_session_owner(session_id: str, new_owner: str) -> dict:
    client = get_client()
    result = client.table("sessions").update({"owner_id": new_owner}).eq("id", session_id).execute()
    return result.data[0] if result.data else {}

def update_session_status(session_id: str, status: str) -> dict:
    client = get_client()
    result = client.table("sessions").update({"status": status}).eq("id", session_id).execute()
    return result.data[0] if result.data else {}

def delete_session(session_id: str) -> None:
    client = get_client()
    client.table("sessions").delete().eq("id", session_id).execute()