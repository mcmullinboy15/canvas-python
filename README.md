# Canvas Python
### Canvas LMS from Instructure
Endpoint Documentation from https://canvas.instructure.com/doc/api/

#

## Getting Started:

>### Get Access Token from canvas settings
+ Go to `settings` on your canvas page
+ Scroll down to Approved Integrations
+ Click: <button>+ New Access Token</button>
  + Purpose: `canvas-python`
  + Leave Blank (token won't work after date, if specified)
+ Copy Access Token

>### Get School ID
+ Look at the url in your browser and remember/save the ID(prefix) `<prefix>.instructure.com`

>### Credentials and Config
+ uses folder `~\.canvas`, with files:
  + credentials
    + access_token
  + config 
    + base_url
+ `utils/setup.py` contains helpful functions for setting this up


## How to use:

>### CANVAS_REST(_REST)

>##### prefixed with <GET: get>, <UPDATE: update>, <DELETE: delete>, and <CREATE: create> if and only if functionality is allowed by api.
  + <>_self
  + <>_profile
  + <>_settings
  + get_colors
  + get_course_nicknames

  + <>_courses
  + <>_assignments

  + <>_planner_items
  + <>_planner_notes
  + <>_planner_overrides
  + mark_complete

  + <>_todos
  + <>_notifications

  + <>_calendar_events
  + <>_upcoming_events

  + <>_inbox
  + create_conversation

  + get_folders
  + get_course_folders
  + get_users_folders
  + get_files
  + get_my_folders


>#### Download Folders and Files
+ `get_course_folders` or `get_my_folders` returns a List of Folder objects, which can be downloaded or used to query sub-folders and files inside it.

        for folder in api.get_course_folders(course_id="<course_id>"):
            # folder.download()
            for sub_folder in folder.folders():
                # sub_folder.download()
                for file in sub_folder.files():
                    print(file.id, file.filename)
                    # file.download()



>### Utils 
  - check utils `__init__.py` for setup help and help functions.