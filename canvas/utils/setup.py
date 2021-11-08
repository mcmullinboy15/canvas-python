from canvas import utils
import os


def check_setup():
    if not os.path.isdir(utils.CANVAS_DIR):
        return False

    if not utils.get_default_credentials():
        return False

    if not utils.get_default_config():
        return False

    if not utils.get_access_token():
        return False

    return True


def run_setup(force: bool=False):
    if not os.path.isdir(utils.CANVAS_DIR):
        print("Creating ~\.canvas folder")
        os.mkdir(utils.CANVAS_DIR)

    if force or not utils.get_access_token():
        access_token = input("Access Token: ")
        if access_token and utils.prompt("Are you sure?"):
            utils.save_access_token(access_token)

    if force or not utils.get_base_url():
        base_url = utils.prompt("URL or School prefix?", {"prefix": True, "url": False, "pass": None})
        if base_url is None:
            pass
        elif base_url:
            utils.save_school_prefix(input("Prefix: "))
        else:
            utils.save_school_url(input("URL: "))

    if force or not utils.get_api_version():
        api_version = input("API Token (default='v1'): ")
        if api_version:
            utils.save_api_version(api_version=api_version)

    return True