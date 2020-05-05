import os

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
from rasa_core.utils import read_yaml_file, read_yaml_string

logger = logging.getLogger(__name__)


class ContentStore(object):
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

    @property
    def answers(self):
        return self.db["answers"]

    @property
    def options(self):
        return self.db["options"]

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
            return stored
        else:
            return None

    def get_utter(self, page_id, utter_name):
        stored = self.answers.find_one({"page_id": page_id, "utter_name": utter_name})

        # look for conversations which have used an `int` page_id in the past
        # and update them.
        if stored is None and page_id.isdigit():
            from pymongo import ReturnDocument
            stored = self.answers.find_one_and_update(
                {"page_id": int(page_id), "utter_name": utter_name},
                {"$set": {"page_id": str(page_id), "utter_name": utter_name}},
                return_document=ReturnDocument.AFTER)

        return stored

    def update_utter(self, page_id, utter_name, data):
        from pymongo import ReturnDocument
        stored = self.answers.find_one_and_update(
            {"page_id": page_id, "utter_name": utter_name},
            {"$set": data},
            return_document=ReturnDocument.AFTER)

        return stored

    def init_answers(self, page_id):
        data = read_yaml_file("init/default_answers.yml")
        data = data["templates"]
        try:
            self.answers.create_index("page_id")
            self.answers.create_index("utter_name")
        except Exception as ex:
            logger.error(ex)
        try:
            for key, value in data.items():
                self.answers.update_one(
                    {"page_id": page_id, "utter_name": key},
                    {"$set": {"utter_payload": value}},
                    upsert=True
                )
        except Exception as ex:
            logger.error(ex)
            return "Error"
        return "ok"

    def update_answers(self, page_id, data):
        data = read_yaml_string(data)
        data = data["templates"]
        try:
            self.answers.create_index("page_id")
            self.answers.create_index("utter_name")
        except Exception as ex:
            logger.error(ex)
        try:
            for key, value in data.items():
                self.answers.update_one(
                    {"page_id": page_id, "utter_name": key},
                    {"$set": {"utter_payload": value}},
                    upsert=True
                )
        except Exception as ex:
            logger.error(ex)
            return "Error"
        return "ok"

    def del_answers(self, page_id):
        self.answers.remove({"page_id": page_id})
