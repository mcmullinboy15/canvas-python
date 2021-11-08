from configparser import ConfigParser
from typing import Any, Dict, List
import dateutil.parser
import datetime
import json
import os

""" Random Utils """
def to_json(resp):
    try:
        return json.loads(resp)
    except json.decoder.JSONDecodeError as e:
        print(resp)


def canvas_datetime(value: str or None) -> datetime.datetime or None:
    if value is None:
        return None
    return datetime.datetime.strptime(value, '%Y-%m-%dT%H:%M:%S%z')


def datetime_simple(value: datetime.datetime) -> str:
    return datetime.datetime.strftime(value, "%Y-%m-%d")


def get_from_hidden_folder(path: str, section: str or None=None, attr: str or None=None, default: Any=None):
    if not os.path.exists(path):
        return None

    config_parser = ConfigParser()
    config_parser.read(path)
    if section is None:
        return config_parser

    config_parser_section: Dict = config_parser[section]
    if attr is None:
        return config_parser_section

    attr_data = config_parser_section.get(attr)
    if attr_data is not None:
        return attr_data

    if default is not None:
        return default

    raise ValueError(f"{attr} is None, please run 'canvas setup' in terminal to setup your environment")
    

def get_default_credentials(attr: str=None, default: Any=None) -> Dict or Any:
    return get_from_hidden_folder(CREDENTIALS_PATH, "default", attr, default=default)

def get_default_config(attr: str=None, default: Any=None) -> Dict or Any:
    return get_from_hidden_folder(CONFIG_PATH, "default", attr, default=default)


def save_to_hidden_folder(path: str, section: str, data: Dict) -> bool:
    config_parser = ConfigParser()
    config_parser[section] = data
    try:
        with open(path, "w") as config_parser_file:
            config_parser.write(config_parser_file)
        return True
    except Exception:
        return False

def save_to_default_credentials(data: Dict) -> bool:
    return save_to_hidden_folder(CREDENTIALS_PATH, "default", data)

def save_to_default_config(data: Dict) -> bool:
    return save_to_hidden_folder(CONFIG_PATH, "default", data)


# Loops until one of the answers are chosen
# if 'answers' is a list then it will return the answer given
# if it is a dict, it will return the value of the answer given
def prompt(prompt: str, answers: List or Dict=None) -> Any or str:
    if answers is None:
        answers = {"y": True, "n": False}

    while True:
        if type(answers) is list:
            display_answers = '/'.join(answers)
        else:
            display_answers = '/'.join([k for k, v in answers.items()])

        answer = input(f"{prompt} ({display_answers}): ")

        if answer == "exit":
            return

        if answer in answers:
            if type(answers) is list:
                return answer
            return answers[answer]
        else:
            print(f"({display_answers}) are the only supported responses")


""" Override Types """
""" From Alpaca but changed to use my .canvas credentials """
class URL(str):
    def __new__(cls, *value):
        """
        note: we use *value and v0 to allow an empty URL string
        """
        if value:
            v0 = value[0]
            if not (isinstance(v0, str) or isinstance(v0, URL)):
                raise TypeError(f'Unexpected type for URL: "{type(v0)}"')
            if not v0.startswith('https://'):
                raise ValueError(f'Passed string value "{v0}" is not an'
                                 f' "https://" URL')
        return str.__new__(cls, *value)


class DATE(str):
    """
    date string in the format YYYY-MM-DD
    """

    def __new__(cls, value):
        if not value:
            raise ValueError('Unexpected empty string in DATE')
        if not isinstance(value, str):
            raise TypeError(f'Unexpected type for DATE: "{type(value)}"')
        if value.count("-") != 2:
            raise ValueError(f'Unexpected date structure. expected '
                             f'"YYYY-MM-DD" got {value}')
        try:
            dateutil.parser.parse(value)
        except Exception as e:
            msg = f"{value} is not a valid date string: {e}"
            raise Exception(msg)
        return str.__new__(cls, value)


class FLOAT(str):
    """
    api allows passing floats or float as strings.
    let's make sure that param passed is one of the two, so we don't pass
    invalid strings all the way to the servers.
    """

    def __new__(cls, value):
        if isinstance(value, float) or isinstance(value, int):
            return value
        if isinstance(value, str):
            return float(value.strip())
        raise ValueError(f'Unexpected float format "{value}"')


""" Canvas Related Utils """
CANVAS_DIR = f"{os.path.expanduser('~')}\\.canvas"
CREDENTIALS_PATH = f"{CANVAS_DIR}\\credentials"
CONFIG_PATH = f"{CANVAS_DIR}\\config"


def save_access_token(access_token: str) -> bool:
    return save_to_default_credentials({"access_token": access_token})

def save_school_url(school_url: str) -> bool:
    return save_to_default_config({"base_url": school_url})

def save_school_prefix(school_prefix: str) -> bool:
    return save_to_default_config({"base_url": f"https://{school_prefix}.instructure.com"})

def save_api_version(api_version: str) -> bool:
    return save_to_default_config({"api_version": api_version})

def clear_config_and_credentials():
    save_to_default_config({"api_version": None, "base_url": None})
    save_to_default_credentials({"access_token": None})


def get_access_token() -> str:
    return get_default_credentials("access_token")

def get_api_version() -> str:
    return get_default_config("api_version", "v1")


def get_base_url(include_version: bool=True) -> URL or None:
    var: str = get_default_config("base_url")
    if var is not None:
        api_version = get_api_version() if include_version else ""
        return URL(var.rstrip('/') + "/api/" + api_version)


def prompt_get_course(self, courses):
    course_list = [f'{course["name"]}({idx})' for idx, course in enumerate(courses)]
    return courses[
        prompt(prompt=f"Select a course [{course_list}]: ",
            answers={
                f"{idx}": idx
                for idx, course in enumerate(courses)
            })
        ]["id"]