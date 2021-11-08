import datetime
from os import path
from requests.exceptions import HTTPError
from typing import List, Dict, Any
import requests
from datetime import datetime as dt, timedelta


from canvas import DEBUG
from canvas.utils.models import (
    User,
    Profile,
    
    Folder,
    File,

    Course,
    Entity,
    Todo,
    Notification,
    Conversation,
    UpcomingEvent,
    PlannerItem,
    PlannerNote,
    PlannerOverride,
    CalendarEvent,
    PlannerCalendarEvent,
    Assignment,
    PlannerAssignment,
    PlannerAnnouncement
)
from canvas.utils import (
    URL,
    get_access_token,
    get_api_version,
    get_base_url
)


class IllegalArgumentError(ValueError):
    pass

class RetryException(Exception):
    pass

class APIError(Exception):
    """
    Represent API related error.
    error.status_code will have http status code.
    """

    def __init__(self, error, http_error=None):
        super().__init__(error['message'])
        self._error = error
        self._http_error = http_error

    @property
    def code(self):
        return self._error['code']

    @property
    def status_code(self):
        http_error = self._http_error
        if http_error is not None and hasattr(http_error, 'response'):
            return http_error.response.status_code

    @property
    def request(self):
        if self._http_error is not None:
            return self._http_error.request

    @property
    def response(self):
        if self._http_error is not None:
            return self._http_error.response


class _REST:
    def __init__(
        self,
        access_token: str = None,
        base_url: URL = None,
        api_version: str = None,
        use_raw_data: bool = False,
        options=None
    ):
        """
        :Parameters
            use_raw_data: DISABLED - return api response raw or wrap it with Entity objects.
        """

        self._access_token  = access_token  or get_access_token()
        self._base_url: URL = URL(base_url) if base_url else get_base_url(include_version=False)
        self._api_version   = api_version   or get_api_version()
        self._session       = requests.Session()
        self._use_raw_data  = use_raw_data

        self._retry = 3
        self.options = options or {}

    def _request(
        self,
        method,
        path,
        data=None,
        base_url: URL = None,
        api_version: str = None,
        url: str = None,
        *args, **kwargs
    ):
        base_url = base_url or self._base_url
        version = api_version if api_version else self._api_version
        # if full_url is not None then use the whole url only for the request
        url: URL = URL(url) if url else URL(base_url + version + path)
        headers = {'Authorization': 'Bearer ' + self._access_token}

        opts = {
            'headers': headers,
            # Since we allow users to set endpoint URL via env var,
            # human error to put non-SSL endpoint could exploit
            # uncanny issues in non-GET request redirecting http->https.
            # It's better to fail early if the URL isn't right.
            'allow_redirects': False,
        }
        if method.upper() == 'GET':
            opts['params'] = data
        else:
            opts['json'] = data

        return self._one_request(method, url, opts, *args, **kwargs)

    def _one_request(self, method: str, url: URL, opts: dict, *args, **kwargs):
        """
        Perform one request, possibly raising RetryException in the case
        the response is 429. Otherwise, if error text contain "code" string,
        then it decodes to json object and returns APIError.
        Returns the body json in the 200 status.
        """

        resp = self._session.request(method, url, *args, **opts, **kwargs)

        try:
            resp.raise_for_status()

        except HTTPError as http_error:

            # retry if we hit Rate Limit
            if 'code' in resp.text:
                error = resp.json()
                if 'code' in error:
                    raise APIError(error, http_error)
            else:
                raise

        if resp.text != '':
            return resp.json()

        return None

    def get(self, path=None, data=None, *args, **kwargs):
        return self._request('GET', path, data, *args, **kwargs)
    
    def post(self, path=None, data=None, *args, **kwargs):
        return self._request('POST', path, data, *args, **kwargs)
    
    def put(self, path=None, data=None, *args, **kwargs):
        return self._request('PUT', path, data, *args, **kwargs)
    
    def patch(self, path=None, data=None, *args, **kwargs):
        return self._request('PATCH', path, data, *args, **kwargs)
    
    def delete(self, path=None, data=None, *args, **kwargs):
        return self._request('DELETE', path, data, *args, **kwargs)

    def list_entities_from_endpoint(self,
        path: str=None,
        entity: Entity=None,
        entity_type_key: str=None,
        entity_map: Dict[str, Entity]={},
        url: str=None,
        *args, **kwargs) -> List[Entity]:
        """
        :Parameters
            path: API Endpoint to get list of data
            entity: SubClass of Entity that you want all elements to be converted to
            if entity is None:
                entity_type_key: used as the key to get the type name from the element
                entity_map: key is the type name in the element, value is the Class to use

        :Usage
            self.list_entities_from_endpoint(
                path="/planner_notes",
                entity=PlannerNote
            )
            self.list_entities_from_endpoint(
                path="/planner/items",
                entity_type_key='plannable_type',
                entity_map={
                    'planner_note': PlannerNote,
                    'calendar_event': PlannerCalendarEvent,
                    'assignment': PlannerAssignment,
                    'announcement': PlannerAnnouncement,
                    'default': PlannerItem,
                }
            )
            
        """

        # Pre Checks
        if entity is None and (entity_type_key is None or entity_map is None):
            raise IllegalArgumentError("If entity is None, entity_type_key and entity_map cannot")

        # If entity is set and subclass of Entity, convert everything to that Class
        if entity is not None and issubclass(entity, Entity):
            return [entity(raw=el, client=self) for el in self.get(path=path, url=url, *args, **kwargs)]

        if 'default' not in entity_map:
            raise IllegalArgumentError("'default' has to be provided in entity_map")


        # Here 'entity_type_key' and 'entity_map' should be set.
        #   :entity_type_key gets the corresponding value from the element
        #   :entity_map pairs the elements 'entity_type_key' to the Class 
        resp_list: List[Entity] = []
        get_list: List[Dict] = self.get(path=path, url=url, *args, **kwargs)
        for el in get_list:
            entity_based_key_value = el.get(entity_type_key)
            entity_class: Entity = entity_map.get(entity_based_key_value, entity_map['default'])
            resp_list.append(entity_class(raw=el, client=self))

        return resp_list


class CANVAS_REST(_REST):

    def get_self(self) -> User:
        return User(raw=self.get("/users/self"), client=self)
    def update_self(self, data: Dict[str, str]):
        """
        :Parameters
            data: use exact keys in dict
                user[name]: string  =  The full name of the user. This name will be used by teacher for grading.
                user[short_name]: string  =  User's name as it will be displayed in discussions, messages, and comments.
                user[sortable_name]: string  =  User's name as used to sort alphabetically in lists.
                user[time_zone]: string  =  The time zone for the user. Allowed time zones are IANA time zones or friendlier Ruby on Rails time zones.
                user[email]: string  =  The default email address of the user.
                user[locale]: string  =  The user's preferred language, from the list of languages Canvas supports. This is in RFC-5646 format.
                user[avatar][token]: string  =  A unique representation of the avatar record to assign as the user's current avatar. This token can be obtained from the user avatars endpoint. This supersedes the user [avatar] [url] argument, and if both are included the url will be ignored. Note: this is an internal representation and is subject to change without notice. It should be consumed with this api endpoint and used in the user update endpoint, and should not be constructed by the client.
                user[avatar][url]: string  =  To set the user's avatar to point to an external url, do not include a token and instead pass the url here. Warning: For maximum compatibility, please use 128 px square images.
                user[title]: string  =  Sets a title on the user profile. (See Get user profile.) Profiles must be enabled on the root account.
                user[bio]: string  =  Sets a bio on the user profile. (See Get user profile.) Profiles must be enabled on the root account.
                user[pronouns]: string  =  Sets pronouns on the user profile. Passing an empty string will empty the user's pronouns Only Available Pronouns set on the root account are allowed Adding and changing pronouns must be enabled on the root account.
                user[event]: string  =  suspends or unsuspends all logins for this user that the calling user has permission to
                    Allowed values: [ suspend, unsuspend ]
        """
        return self.put(path="/users/self", data=data)

    def get_settings(self, course_id: str or int=None) -> Dict:        
        path = "/users/self/settings"
        if course_id is not None:
            path = f"/courses/{course_id}/settings"
        return self.get(path=path)

    def update_settings(self, data: Dict[str, Any]):
        """
        data:
            manual_mark_as_read		boolean	
                If true, require user to manually mark discussion posts as read (don't auto-mark as read).
            release_notes_badge_disabled		boolean	
                If true, hide the badge for new release notes.
            collapse_global_nav		boolean	
                If true, the user's page loads with the global navigation collapsed
            hide_dashcard_color_overlays		boolean	
                If true, images on course cards will be presented without being tinted to match the course color.
            comment_library_suggestions_enabled		boolean	
                If true, suggestions within the comment library will be shown.
            elementary_dashboard_disabled		boolean	
                If true, will display the user's preferred class Canvas dashboard view instead of the canvas for elementary view.
        """
        return self.put(path="/users/self/settings", data=data)

    def get_profile(self) -> Dict:
        return Profile(self.get(path="/users/self/profile"), client=self)
    def update_profile(self, data: Dict[str, Any]):
        return self.put(path="/users/self/profile", data=data)

    def get_courses(self) -> List[Course]:
        return self.list_entities_from_endpoint(path="/courses", entity=Course)

    # grades
    def get_planner_items(self, future_days=2, per_page=300) -> List[PlannerItem]:
        
        # For Planner Only
        end = dt.strftime(dt.today() + timedelta(days=future_days), '%Y-%m-%dT00:00:00.000Z')

        return self.list_entities_from_endpoint(
            path="/planner/items",
            entity_type_key='plannable_type',
            entity_map={
                'planner_note': PlannerNote,
                'calendar_event': PlannerCalendarEvent,
                'assignment': PlannerAssignment,
                'announcement': PlannerAnnouncement,
                'default': PlannerItem,
            },
            data={
                "end_date": end,
                "per_page": per_page
            })
    def update_planner_items(self):
        raise NotImplementedError
    def delete_planner_items(self):
        raise NotImplementedError

    def get_planner_notes(self) -> List[PlannerNote]:
        return self.list_entities_from_endpoint(
            path="/planner_notes", entity=PlannerNote)
    def create_planner_notes(self, title, details, todo_date:datetime.datetime, course_id):
        """
        Parameter		Type	Description
        title: str = The title of the planner note.
        details: str = Text of the planner note.
        todo_date: Date = The date where this planner note should appear in the planner. The value should be formatted as: yyyy-mm-dd.
        course_id: int = The ID of the course to associate with the planner note. The caller must be able to view the course in order to associate it with a planner note.
        linked_object_type: string = The type of a learning object to link to this planner note. Must be used in conjunction wtih linked_object_id and course_id. Valid linked_object_type values are: 'announcement', 'assignment', 'discussion_topic', 'wiki_page', 'quiz'
        linked_object_id: int = The id of a learning object to link to this planner note. Must be used in conjunction with linked_object_type and course_id. The object must be in the same course as specified by course_id. If the title argument is not provided, the planner note will use the learning object's title as its title. Only one planner note may be linked to a specific learning object.
        """
        return self.list_entities_from_endpoint(
            path="/planner_notes", entity=PlannerNote)
    def update_planner_notes(self, note_id: str, data: Dict):
        """
        title: str = The title of the planner note.
        details: str	= Text of the planner note.
        todo_date: Date	= The date where this planner note should appear in the planner. The value should be formatted as: yyyy-mm-dd.
        course_id: int = The ID of the course to associate with the planner note. The caller must be able to view the course in order to associate it with a planner note. Use a null or empty value to remove a planner note from a course. Note that if the planner note is linked to a learning object, its course_id cannot be changed.
        """
        return self.put(path=f"/planner_notes/{note_id}", data=data)
    def delete_planner_notes(self, note_id):
        return self.delete(path=f"/planner_notes/{note_id}")

    def get_planner_overrides(self, override_id=None):
        return self.list_entities_from_endpoint(
            path="/planner/overrides", entity=PlannerOverride)
    def create_planner_overrides(self, data: Dict):
        return self.post(path="/planner/overrides", data=data)
    def update_planner_overrides(self, override_id: str, data: Dict):
        """
        marked_complete: str = determines whether the planner item is marked as completed
        dismissed: str = determines whether the planner item shows in the opportunities list
        """
        return self.put(path=f"/planner/overrides/{override_id}", data=data)
    def mark_complete(self, override_id:str, side:bool=True):
        return self.update_planner_overrides(
            override_id=override_id,
            data={"marked_complete": side})
    def delete_planner_overrides(self, override_id: str):
        return self.delete(path=f"/planner/overrides/{override_id}")

    def get_calendar_events(self) -> List[CalendarEvent]:
        return self.list_entities_from_endpoint(
            path="/users/self/calendar_events", entity=CalendarEvent)
    def create_calendar_events(self, title, description, context_code:str=None, start_at:datetime.datetime=None, end_at: datetime.datetime=None, all_day: bool=False, *args, **kwargs):
        return self.push_to_calendar_events("UPDATE", title, description, context_code, start_at, end_at, all_day, *args, **kwargs)
    def update_calendar_events(self, title, description, context_code:str=None, start_at:datetime.datetime=None, end_at: datetime.datetime=None, all_day: bool=False, *args, **kwargs):
        # TODO: I probably need to add an ID 
        return self.push_to_calendar_events("CREATE", title, description, context_code, start_at, end_at, all_day, *args, **kwargs)
    def push_to_calendar_events(self, method, title, description, context_code:str=None, start_at:datetime.datetime=None, end_at: datetime.datetime=None, all_day: bool=False, *args, **kwargs):
        """
        https://canvas.instructure.com/doc/api/calendar_events.html
        Main params, check documentation for more parameters, passed using kwargs
            calendar_event[context_code]: Required: str = Context code of the course/group/user whose calendar this event should be added to.
                default: user_<user_id>, other: course_123, group_123
            calendar_event[title]: str = Short title for the calendar event.
            calendar_event[description]: str = Longer HTML description of the event.
            calendar_event[start_at]: DateTime = Start date/time of the event.
            calendar_event[end_at]: DateTime = End date/time of the event.
            calendar_event[all_day]: boolean = When true event is considered to span the whole day and times are ignored.
        """
        if method == "UPDATE":
            request_method = self.put
        elif method == "CREATE":
            request_method = self.post
        else:
            raise IllegalArgumentError("only UPDATE or CREATE are allowed as the method")

        return request_method(
            path="/calendar_events",
            data={
                "context_code": context_code,
                "title": title, 
                "description": description,
                "start_at": start_at,
                "end_at": end_at,
                "all_day": all_day,
                **kwargs
            })
    def delete_calendar_events(self, calendar_event_id):
        return self.delete(path=f"/calendar_events/{calendar_event_id}")
    
    def get_upcoming_events(self, course_id: str or int=None) -> List[UpcomingEvent]:
        path = "/users/self/upcoming_events"
        if course_id is not None:
            path = f"/courses/{course_id}/upcoming_events"
        return self.list_entities_from_endpoint(path=path, entity=UpcomingEvent)
    def update_upcoming_events(self):
        raise NotImplementedError
    def delete_upcoming_events(self):
        raise NotImplementedError

    def get_todos(self, course_id: str or int=None) -> List[Todo]:
        path = "/users/self/todo"
        if course_id is not None:
            path = f"/courses/{course_id}/todo"

        return self.list_entities_from_endpoint(path=path, entity=Todo)

    def get_notifications(self, course_id: str or int=None) -> List[Notification]:
        path = "/users/self/activity_stream"
        if course_id is not None:
            path = f"/courses/{course_id}/activity_stream"
        return reversed(self.list_entities_from_endpoint(path=path, entity=Notification))
    def delete_notifications(self, notification_id=None, clear_all=False):
        notification_id_path = f"/users/self/activity_stream/{notification_id}"
        all_path = f"/users/self/activity_stream"
        self.delete(path=notification_id_path if not clear_all else all_path)

    def get_inbox(self, conversation_id: str=None) -> List[Conversation]:
        return self.list_entities_from_endpoint(
            path=f"/conversations/{conversation_id if conversation_id else ''}", entity=Conversation)
            # TODO, with id returns a Dict not a List
    def create_conversation(self, recipients: List, subject: str, body: str, force_new: bool=False, context_code:str=None, **kwargs):
        """
        recipients[]	Required	string	= An array of recipient ids. These may be user ids or course/group ids prefixed with “course_” or “group_” respectively, e.g. recipients[]=1&recipients=2&recipients[]=course_3. If the course/group has over 100 enrollments, 'bulk_message' and 'group_conversation' must be set to true.
        subject		string	= The subject of the conversation. This is ignored when reusing a conversation. Maximum length is 255 characters.
        body	Required	string	= The message to be sent
        force_new		boolean	= Forces a new message to be created, even if there is an existing private conversation.
        group_conversation		boolean	= Defaults to false. When false, individual private conversations will be created with each recipient. If true, this will be a group conversation (i.e. all recipients may see all messages and replies). Must be set true if the number of recipients is over the set maximum (default is 100).
        attachment_ids[]		string	= An array of attachments ids. These must be files that have been previously uploaded to the sender's “conversation attachments” folder.
        media_comment_id		string	= Media comment id of an audio of video file to be associated with this message.
        media_comment_type		string	= Type of the associated media file
            Allowed values: audio, video
        user_note		boolean	= Will add a faculty journal entry for each recipient as long as the user making the api call has permission, the recipient is a student and faculty journals are enabled in the account.
        mode		string	= Determines whether the messages will be created/sent synchronously or asynchronously. Defaults to sync, and this option is ignored if this is a group conversation or there is just one recipient (i.e. it must be a bulk private message). When sent async, the response will be an empty array (batch status can be queried via the batches API)
            Allowed values: sync, async
        scope		string	= Used when generating “visible” in the API response. See the explanation under the index API action
            Allowed values: unread, starred, archived
        filter[]		string	= Used when generating “visible” in the API response. See the explanation under the index API action
        filter_mode		string	= Used when generating “visible” in the API response. See the explanation under the index API action
            Allowed values: and, or, default or
        context_code		string	= The course or group that is the context for this conversation. Same format as courses or groups in the recipients argument.
        """
        self.post(path="/conversations", data={
            "recipients": recipients, 
            "subject": subject, 
            "body": body, 
            "force_new": force_new, 
            "context_code": context_code,
            **kwargs
        })
    def update_inbox(self):
        raise NotImplementedError
    def delete_inbox(self):
        raise NotImplementedError

    def get_assignments(self, course_id: str or int) -> List[Assignment]:
        path = f"/courses/{course_id}/assignments"
        return self.list_entities_from_endpoint(path=path, entity=Assignment)
    def update_assignments(self):
        raise NotImplementedError


    """ MISC """
    def get_colors(self) -> Dict:
        return self.get(path="/users/self/colors")
    def update_colors(self, course_id: str or int=None, hexcode: str=None):
        """ The hexcode of the color to set for the context, if you choose 
            to pass the hexcode as a query parameter rather than in the request 
            body you should NOT include the '#' unless you escape it first. """
        return self.put(path=f"/users/self/colors/course_{course_id}",
            data={"hexcode": hexcode})
    def get_course_nicknames(self, course_id: str or int=None) -> List or Dict:
        return self.get(path=f"/users/self/course_nicknames{'/'+course_id if course_id else ''}")
    def update_course_nicknames(self):
        raise NotImplementedError

    # def CUSTOM_DATA
    # https://canvas.instructure.com/doc/api/users.html
    # PUT /api/v1/users/:user_id/custom_data(/*scope)

    # Files
    # https://canvas.instructure.com/doc/api/files.html
    def get_folders(self,
        folder_root: str = None,
        root_id: str = None,
        folder_id: str or int=None) -> List[Folder]:
        """
        :Parameters
            folder_root: [ users, courses, groups, folders ] = "folders"
            root_id:     [ self, :id ] = None
            folder_id:   [ :id ] = None
        """
        folder_id = folder_id or ''
        if folder_id:
            return self.list_entities_from_endpoint(
                path=f"{f'/{folder_root}' if folder_root else ''}{f'/{root_id}' if root_id else ''}/files/folder/{folder_id}",
                entity=Folder)
        return self.list_entities_from_endpoint(
            path=f"{f'/{folder_root}' if folder_root else ''}{f'/{root_id}' if root_id else ''}/folders/{folder_id}{f'/folders' if not root_id and not folder_root else ''}",
            entity=Folder)

    def get_course_folders(self, course_id: str, folder_id: str or int=None) -> List[Folder]:
        return self.get_folders(folder_root="courses", root_id=course_id, folder_id=folder_id)
    def get_users_folders(self, folder_id: str or int=None) -> List[Folder]:
        return self.get_folders(folder_root="users",   root_id="self",    folder_id=folder_id)

    # basic ones use /folders/:id 
    def create_folder(self):
        raise NotImplementedError
    # these two are used just to make sure we know what the root folder is
    def create_course_folder(self):
        raise NotImplementedError
    def create_my_folder(self):
        raise NotImplementedError

    def update_folder(self):
        """ 
        name:       string = The new name of the folder
        parent_folder_id: string = The id of the folder to move this folder into. The new folder must be in the same context as the original parent folder.
        lock_at:    DateTime = The datetime to lock the folder at
        unlock_at:  DateTime = The datetime to unlock the folder at
        locked:     boolean = Flag the folder as locked
        hidden:     boolean	= Flag the folder as hidden
        position:   integer = Set an explicit sort position for the folder
        """
        raise NotImplementedError
    def delete_folder(self):
        raise NotImplementedError
        

    def get_files(self, folder_id: str=None, file_id: str=None):
        path = f"/folders"
        if folder_id:
            path += f"/{folder_id}"
        if file_id:
            path += f"/{file_id}"
        path += "/files"
        return self.list_entities_from_endpoint(path, entity=File)

    def get_my_folders(self) -> List[Folder]:
        return self.get(path="/users/self/folders")
    def get_my_files_by_path(self, path: str=None) -> List[Folder]:
        return self.get(path=f"/users/self/folders/by_path{path if path else ''}")
    # def get_course_folders(self, course_id: str) -> List[Folder]:
    #     return self.get(path=f"/courses/{course_id}/folders",)
    def get_course_files_by_path(self, course_id: str, path: str=None) -> List[Folder]:
        return self.get(path=f"/courses/{course_id}/folders/by_path{path if path else ''}")

    def upload_file(self):
        raise NotImplementedError
    def upload_course_file(self):
        raise NotImplementedError
    def upload_my_file(self):
        raise NotImplementedError