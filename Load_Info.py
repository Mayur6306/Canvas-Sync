import requests
import os
from dotenv import load_dotenv

load_dotenv()

# Local Institution's Canvas' Domain URL
CANVAS_URL = os.getenv("CANVAS_URL")

# User's Canvas' Access Token
CANVAS_TOKEN = os.getenv("CANVAS_TOKEN")


# Returns User's Active course ids
def get_courses(canvas_url: str, canvas_token: str) -> dict:

    courses = requests.get(
    f"https://{canvas_url}/api/v1/courses?enrollment_state=active&include[]=term",
    headers={"Authorization":f"Bearer {canvas_token}","Accept":"*/*"},
    ).json()

    courses_info = {course["name"]:course['id'] for course in courses}

    return courses_info


def get_assignments(canvas_url: str, courses: list[int], canvas_token: str) -> dict:

    assignments = []

    for course_name, course_id in courses.items():
        
        assigments_info = requests.get(
        f"https://{canvas_url}/api/v1/courses/{course_id}/assignments?include[]=submission&order_by=due_at&per_page=100",
        headers={"Authorization":f"Bearer {canvas_token}","Accept":"*/*"},
        ).json()

        
        for info in assigments_info:


            # Visible Columns[course_name, assignment_name, due_date, days_left, priority, status, submitted, notes, link,
            # Hidden Hidden: .sync_id, .source, .due_date_utc, .content_hash, .created_at, .updated_at, .last_synced]
            assignment = {
                "course_name":course_name,
                "assignment":info['name'],
                "submitted": 'Yes' if info['submission']['workflow_state'] in ['graded', 'submitted', 'pending_review'] else 'No',
                "link":info['html_url'],
                "sync_id":f'canvas:{course_id}:{info['id']}', 
                "source":'canvas',
                "due_date_utc":info['due_at'],
                "updated_at":info['updated_at']
                }
            assignments.append(assignment)
    
    return assignments
        


 
courses = get_courses(CANVAS_URL, CANVAS_TOKEN)

print(courses)
print(get_assignments(CANVAS_URL, courses, CANVAS_TOKEN))
