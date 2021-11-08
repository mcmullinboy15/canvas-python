import os
from typing import Dict, List
import pandas as pd
import requests
import pprint
import re

class IllegalArgumentError(ValueError):
    pass



ISO8601YMD = re.compile(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z')


class Entity:
    '''  This helper class provides property access (the "dot notation")
    to the json object, backed by the original object stored in the _raw
    field.  '''

    def __init__(self, raw: dict, client, dict_to_entity: dict=None):
        self._raw = raw
        if not isinstance(self._raw, dict):
            raise IllegalArgumentError("parameter raw must be dict")

        self.dict_to_entity = dict_to_entity or {}
        
        from canvas.utils.rest import CANVAS_REST
        self.client: CANVAS_REST = client

    def __getattr__(self, key):
        # if it's not in _raw then pretend I'm not here
        if key not in self._raw:
            print(self)
            return super().__getattribute__(key)
            
        val = self._raw[key]
        if isinstance(val, str):
            # if its a date convert to datetime
            if (key.endswith('_at') or \
                    key.endswith('_date')) and \
                        ISO8601YMD.match(val):
                return pd.Timestamp(val)

            return val
        if isinstance(val, Dict):
            
            if key in self.dict_to_entity:
                return self.dict_to_entity.get(key)(raw=val, client=self.client)

            return val
        else:
            return val

    def __repr__(self):
        return '{name}({raw})'.format(
            name=self.__class__.__name__,
            raw=pprint.pformat(self._raw, indent=4),
        )


class Course(Entity):
    """
    {
        'account_id': 1,
        'apply_assignment_group_weights': False,
        'blueprint': False,
        'calendar': {'ics': 'https://umich.instructure.com/feeds/calendars/course_V0W6SczRRb8yacgrkaQsLw9RNMSJrp2YfciWDbuc.ics'},
        'course_code': 'Grad School 101',
        'course_color': None,
        'created_at': '2021-04-08T18:11:46Z',
        'default_view': 'wiki',
        'end_at': None,
        'enrollment_term_id': 53,
        'enrollments': [{'enrollment_state': 'active',
                        'limit_privileges_to_course_section': False,
                        'role': 'StudentEnrollment',
                        'role_id': 14,
                        'type': 'student',
                        'user_id': 647989}],
        'friendly_name': None,
        'grade_passback_setting': None,
        'grading_standard_id': None,
        'hide_final_grades': False,
        'homeroom_course': False,
        'id': 482846,
        'is_public': False,
        'is_public_to_auth_users': False,
        'license': 'private',
        'name': 'Grad School 101',
        'overridden_course_visibility': '',
        'public_syllabus': False,
        'public_syllabus_to_auth': False,
        'restrict_enrollments_to_course_dates': False,
        'root_account_id': 1,
        'start_at': '2021-08-03T19:53:05Z',
        'storage_quota_mb': 12000,
        'template': False,
        'time_zone': 'America/New_York',
        'uuid': 'V0W6SczRRb8yacgrkaQsLw9RNMSJrp2YfciWDbuc',
        'workflow_state': 'available'
    }
    """
    def folders(self):
        raise NotImplementedError
    def files(self):
        raise NotImplementedError
    def todo(self):
        raise NotImplementedError
    def settings(self):
        raise NotImplementedError
    def todo(self):
        raise NotImplementedError
    


class PlannerItem(Entity):
    """
    {
        'context_type': 'Course',
        'course_id': 466754,
        'plannable_id': 1452249,
        'planner_override': {
            'plannable_id': 1452249,
            'plannable_type': 'announcement',
            'id': 6727667,
            'user_id': 647989,
            'workflow_state': 'active',
            'marked_complete': True,
            'deleted_at': None,
            'created_at': '2021-09-18T03:09:05Z',
            'updated_at': '2021-09-18T03:09:05Z',
            'dismissed': False,
            'assignment_id': None
        },
        'plannable_type': 'announcement',
        'new_activity': False,
        'submissions': False,
        'plannable_date': '2021-09-01T00:51:28Z',
        'plannable': {
            'id': 1452249,
            'title': 'Quicksort',
            'unread_count': 0,
            'read_state': 'read',
            'created_at': '2021-09-01T00:51:28Z',
            'updated_at': '2021-09-01T00:51:28Z'
        },
        'html_url': '/courses/466754/discussion_topics/1452249',
        'context_name': 'EECS 587 - Parallel Computing',
        'context_image': None
    }
    """
    # Key Count
    # {'plannable_id': 25, 'planner_override': 25,
    #  'plannable_type': 25, 'plannable_date': 25,
    #  'plannable': 25, 'new_activity': 25, 'submissions': 25,
    #  'context_type': 24, 'html_url': 24, 'context_name': 24,
    #  'course_id': 22, 'context_image': 22}
    def __init__(self, raw, client):
        super().__init__(
            raw=raw,
            client=client,
            dict_to_entity={
                'planner_override': PlannerOverride,
                'plannable': Plannable })

        # self.plannable_id = None
        # self.plannable_date = None
        # self.plannable_type = None
        # self.planner_override = None
        # self.plannable = None
        # self.submissions = None
        # self.new_activity = None

    def mark_complete(self, side=True):
        if not self.planner_override:
            return False

        self.client.mark_complete(override_id=self.planner_override.id, side=side)

class PlannerNote(PlannerItem):
    pass

class PlannerOverride(Entity):
    pass

class Plannable(Entity):
    pass


class PlannerCalendarEvent(PlannerItem):
    pass
class CalendarEvent(Entity):
    """Don't need to use"""
    pass
class PlannerAssignment(PlannerItem):
    pass
class Assignment(Entity):
    """Don't need to use"""
    pass
class PlannerAnnouncement(PlannerItem):
    pass
class Announcement(Entity):
    """Don't need to use"""
    pass



class Todo(Entity):
    pass

class Notification(Entity):
    pass

class Conversation(Entity):
    pass

class UpcomingEvent(Entity):
    pass

class User(Entity):
    pass

class Profile(Entity):
    pass


""" File/Folder """
class Folder(Entity):
    """
    {
        'can_upload': False,
        'context_id': 466754,
        'context_type': 'Course',
        'created_at': '2021-09-03T04:05:49Z',
        'files_count': 2,
        'files_url': 'https://umich.instructure.com/api/v1/folders/3465798/files',
        'folders_count': 0,
        'folders_url': 'https://umich.instructure.com/api/v1/folders/3465798/folders',
        'for_submissions': False,
        'full_name': 'course files/Assignments',
        'hidden': None,
        'hidden_for_user': False,
        'id': 3465798,
        'lock_at': None,
        'locked': False,
        'locked_for_user': False,
        'name': 'Assignments',
        'parent_folder_id': 3420444,
        'position': 2,
        'unlock_at': None,
        'updated_at': '2021-09-03T04:05:49Z'
    }
    """
    def folders(self) -> List['Folder']:
        return self.client.get_folders(folder_id=self.id)

    def files(self) -> List['File']:
        return self.client.get_files(folder_id=self.id)

    def download(self, folder_name: str=None):
        roots = ['my files', 'course files']

        folder_name = folder_name
        if not folder_name:
            folder_name = "tmp/"
        folder_name += self.name if self.name not in roots else ''

        if not os.path.exists(folder_name):
            os.makedirs(folder_name)

        for file in self.files():
            file.download(file_directory=folder_name)

class File(Entity):
    """
    {   
        'content-type': 'application/pdf',
        'created_at': '2021-09-29T22:35:22Z',
        'display_name': '2100930.pdf',
        'filename': '2100930.pdf',
        'folder_id': 3469874,
        'hidden': False,
        'hidden_for_user': False,
        'id': 21991399,
        'lock_at': None,
        'locked': False,
        'locked_for_user': False,
        'media_entry_id': None,
        'mime_class': 'pdf',
        'modified_at': '2021-09-29T22:35:22Z',
        'size': 272049,
        'thumbnail_url': None,
        'unlock_at': None,
        'updated_at': '2021-09-29T22:35:22Z',
        'upload_status': 'success',
        'url': 'https://umich.instructure.com/files/21991399/download?download_frd=1&verifier=bHJljveHhfPSMWFpMHEeiQ8yTGVmRDvsbIjs42mT',
        'uuid': 'bHJljveHhfPSMWFpMHEeiQ8yTGVmRDvsbIjs42mT'
    }
    """
    def download(self, file_directory: str=None, mode='wb'):
        file_directory = file_directory
        if not file_directory:
            file_directory = 'tmp/'
        
        file=f"{file_directory}{'' if file_directory.endswith('/') else '/'}"
        if not os.path.exists(file):
            os.makedirs(file)
        file += self.filename

        r = requests.get(self.url)
        with open(file=file, mode=mode) as f:
            f.write(r.content)

        print("Successfully downloaded file:", file)