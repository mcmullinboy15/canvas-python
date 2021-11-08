import sys
from canvas import utils
from canvas.utils.rest import CANVAS_REST


def get_argparser():
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--access-token",
                        help="Access Token from Canvas Settings (default %(default)s)")
    parser.add_argument("command",
                        help="Main command to be run")
    return parser.parse_args()

def get_commands():
    CRUD_COMMANDS = ["get", "create", "update", "delete"]
    return {
        "self": ["get"],
        "settings": ["get", "update"],
        "profile": ["get"], 
        "courses": ["get"], 
        "planner": [""], 
        "notes": [], 
        "calendar": [],
        "todos": [],
        "notifications": [],
        "inbox": [],
        "assignments": [],
        "colors": [],
        "nickname": [],
        "files": [],
        "folders": []

    }

if __name__ == "__main__":
    CRUD_COMMANDS = ["get", "create", "update", "delete"]

    client = CANVAS_REST()

    method_prefix = "get"
    if len(sys.argv) > 2 and sys.argv[2] in CRUD_COMMANDS:
        method_prefix = sys.argv[2]

    # resp = None
    # exec(f"resp = client.{method_prefix}_{sys.argv[1]}()")
    
    # print(resp)

    course_id = "457389"
    folder_id = "LectureSlides"
    folders = client.get_course_folders(course_id=course_id, folder_id=folder_id)
    print(folders)

    for folder in folders:

        folder.download()