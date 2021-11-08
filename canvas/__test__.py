from os import path
from canvas.utils.models import (
    Course,
    PlannerAssignment,
    PlannerItem,
    PlannerNote
)
from typing import List, Dict
from canvas.utils import get_access_token, get_api_version, get_base_url, prompt
from canvas.utils.setup import check_setup, run_setup
from canvas.utils.rest import CANVAS_REST

from pprint import pprint

SETUP_PROMPT = "You are not setup would you like to setup now?"
if not check_setup() and prompt(SETUP_PROMPT):
    run_setup()


api = CANVAS_REST()

# user = api.get_self()
# print(user)

# courses = api.get_courses()
# for course in courses:
#     print(course.id)

# planner_items = api.get_planner_items()
# for planner in planner_items:
#     print(f"{planner.plannable_type} ({planner.plannable_id})({'O' if not planner.planner_override else 'X' if planner.planner_override.marked_complete else 'X'}): {'' if not planner.plannable else planner.plannable.title}")

# TODO <PlannerItem>.isMarkedComplete()

# calendar_events = api.get_calendar_events()
# for cal in calendar_events:
#     print(cal.id, cal._raw, cal.created_at, cal.updated_at)

# notifications = api.get_notifications()
# for noti in notifications:
#     print(noti.title, "\n", noti.created_at, noti.updated_at)


print(api.get_inbox())