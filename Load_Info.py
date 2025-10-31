import requests
import os
from dotenv import load_dotenv

load_dotenv()

#Local Institution's Canvas' Domain URL
CANVAS_URL = os.getenv("CANVAS_URL")

#User's Canvas' Access Token
CANVAS_TOKEN = os.getenv("CANVAS_TOKEN")


def get_courses(canvas_url: str, canvas_token: str) -> dict:
    response = requests.get(
    f"https://{canvas_url}/api/v1/courses?enrollment_state=active",
    headers={"Authorization":f"Bearer {canvas_token}","Accept":"*/*"},
    )

    return response.json()

def get_assignements(canvas_url: str, course_id: int, canvas_token: str) -> dict:
    response = requests.get(
    f"https://{canvas_url}/api/v1/courses/{course_id}/assignments?include[]=submission?order_by=due_at?per_page=100",
    headers={"Authorization":f"Bearer {canvas_token}","Accept":"*/*"},
    )

    return response.json()


courses = get_courses(CANVAS_URL, CANVAS_TOKEN)

courses_names = {course['id']:course['name'] for course in courses}

print(courses_names)
print(get_assignements(CANVAS_URL,courses[0]['id'],CANVAS_TOKEN))
