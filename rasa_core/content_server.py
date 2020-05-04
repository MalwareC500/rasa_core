import logging
import os
import tempfile
import zipfile
from functools import wraps
from typing import List, Text, Optional, Union, Callable, Any
import random

from flask import Flask, request, abort, Response, jsonify, json
from flask_cors import CORS, cross_origin
from flask_jwt_simple import JWTManager, view_decorators

from rasa_core import utils, constants
from rasa_core.channels import CollectingOutputChannel, UserMessage
from rasa_core.test import test
from rasa_core.events import Event
from rasa_core.domain import Domain
from rasa_core.policies import PolicyEnsemble
from rasa_core.trackers import DialogueStateTracker, EventVerbosity
from rasa_core.version import __version__

from rasa_core.content_store import ContentStore

logger = logging.getLogger(__name__)


def endpoint_app(webhook):
    content = ContentStore("endpoints.yml")
    """Add the content management route.
    Endpoints for changing bot answer, options, ...
    """
    @webhook.route("/content", methods=['GET'])
    def content_health():
        return jsonify({"status": "ok"})

    # Page and bot info management APIs
    @webhook.route("content/<user_id>/pages", methods=["POST"])
    def content_get_pages(user_id):
        return None

    # Answer management APIs
    @webhook.route("/content/<page_id>/answers", methods=["POST"])
    def content_get_answers(page_id):
        """Get answer by page id and utter name
        """
        request_params = request.get_json(force=True)
        print(request_params)
        utter_name = request_params.get("utter_name")
        answer = content.get_utter(page_id, utter_name)
        text = random.choice(answer['utter_payload']['text'])
        if "options" in answer['utter_payload'].keys():
            button = answer['utter_payload']['options']
        else:
            button = None
        return jsonify({"text": text, "button": button})
    
    return webhook