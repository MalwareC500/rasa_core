import itertools

import json
import logging
import pickle
# noinspection PyPep8Naming
from typing import Text, Optional, List, KeysView

from rasa_core.actions.action import ACTION_LISTEN_NAME
from rasa_core.broker import EventChannel
from rasa_core.domain import Domain
from rasa_core.utils import class_from_module_path
from rasa_core.utils import read_yaml_file

logger = logging.getLogger(__name__)

class MongoTokenStore(object):
    def __init__(self,
                 endpoint_file="endpoints.yml",
                 host="mongodb://localhost:27017",
                 db="chatbot",
                 username=None,
                 password=None,
                 auth_source="admin"):
        from pymongo.database import Database
        from pymongo import MongoClient

        try:
            auth = read_yaml_file(endpoint_file)["tracker_store"]
            if auth["type"] == "mongod":
                host = auth["url"]
                db = auth["db"]
                username = auth["username"]
                password = auth["password"]
                auth_source = auth["auth_source"]
        except:
            pass

        self.client = MongoClient(host,
                                  username=username,
                                  password=password,
                                  authSource=auth_source,
                                  # delay connect until process forking is done
                                  connect=False)

        self.db = Database(self.client, db)
        # self._ensure_indices()

    @property
    def answers(self):
        return self.db["answers"]
    
    @property
    def options(self):
        return self.db["options"]

    def _ensure_indices(self):
        self.answers.create_index("page_id")
        self.options.create_index("page_id")

    def get_answers(self, page_id):
        stored = self.answers.find({"page_id": page_id})

        # look for conversations which have used an `int` page_id in the past
        # and update them.
        if stored is None and page_id.isdigit():
            from pymongo import ReturnDocument
            stored = self.answers.find_and_modify(
                {"page_id": int(page_id)},
                {"$set": {"page_id": str(page_id)}},
                return_document=ReturnDocument.AFTER)

        if stored is not None:
            return stored["page_access_token"]
        else:
            return None
