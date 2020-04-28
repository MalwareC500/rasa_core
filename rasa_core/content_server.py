import logging
import os
import tempfile
import zipfile
from functools import wraps
from typing import List, Text, Optional, Union, Callable, Any

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

logger = logging.getLogger(__name__)


def endpoint_app(webhook):
    """Add the content management route.
    Endpoints for changing bot answer, options, ...
    """
    @webhook.route("/content", methods=['GET'])
    def health():
        return jsonify({"status": "ok"})

    @webhook.route("/content/<page_id>/answers", methods=["GET"])
    def get_answers(page_id):
        return None

    