import hashlib
import hmac
import os
import logging
from typing import Text, List, Dict, Any, Callable
from urllib.parse import parse_qs

from fbmessenger import (
    BaseMessenger, MessengerClient, attachments)
from fbmessenger.elements import Text as FBText
from flask import Blueprint, request, jsonify, render_template

from rasa_core.channels.channel import UserMessage, OutputChannel, InputChannel
from rasa_core.token_store import MongoTokenStore
from rasa_core.content_store import ContentStore

logger = logging.getLogger(__name__)


class Messenger(BaseMessenger):
    """Implement a fbmessenger to parse incoming webhooks and send msgs."""

    @classmethod
    def name(cls):
        return "facebook"

    def __init__(self,
                 page_access_token: Text,
                 on_new_message: Callable[[UserMessage], None]) -> None:

        self.page_access_token = page_access_token
        self.on_new_message = on_new_message
        super(Messenger, self).__init__(self.page_access_token)

    @staticmethod
    def _is_audio_message(message: Dict[Text, Any]) -> bool:
        """Check if the users message is a recorced voice message."""
        return (message.get('message') and
                message['message'].get('attachments') and
                message['message']['attachments'][0]['type'] == 'audio')

    @staticmethod
    def _is_user_message(message: Dict[Text, Any]) -> bool:
        """Check if the message is a message from the user"""
        return (message.get('message') and
                message['message'].get('text') and
                not message['message'].get("is_echo"))

    def message(self, message: Dict[Text, Any]) -> None:
        """Handle an incoming event from the fb webhook."""

        if self._is_user_message(message):
            text = message['message']['text']
        elif self._is_audio_message(message):
            attachment = message['message']['attachments'][0]
            text = attachment['payload']['url']
        elif "attachments" in message['message'].keys():
            attachment = message['message']['attachments'][0]
            text = attachment['payload']['url']
        else:
            logger.warning("Received a message from facebook that we can not "
                           "handle. Message: {}".format(message))
            return

        self._handle_user_message(text, self.get_user_id(), self.get_page_id())

    def postback(self, message: Dict[Text, Any]) -> None:
        """Handle a postback (e.g. quick reply button)."""

        text = message['postback']['payload']
        self._handle_user_message(text, self.get_user_id(), self.get_page_id())

    def _handle_user_message(self, text: Text, sender_id: Text, page_id: Text) -> None:
        """Pass on the text to the dialogue engine for processing."""

        out_channel = MessengerBot(self.client)
        user_msg = UserMessage(text, out_channel, sender_id,
                               input_channel=self.name(), page_id=page_id)

        # noinspection PyBroadException
        try:
            self.on_new_message(user_msg)
        except Exception:
            logger.exception("Exception when trying to handle webhook "
                             "for facebook message.")
            pass

    def delivery(self, message: Dict[Text, Any]) -> None:
        """Do nothing. Method to handle `message_deliveries`"""
        pass

    def read(self, message: Dict[Text, Any]) -> None:
        """Do nothing. Method to handle `message_reads`"""
        pass

    def account_linking(self, message: Dict[Text, Any]) -> None:
        """Do nothing. Method to handle `account_linking`"""
        pass

    def optin(self, message: Dict[Text, Any]) -> None:
        """Do nothing. Method to handle `messaging_optins`"""
        pass


class MessengerBot(OutputChannel):
    """A bot that uses fb-messenger to communicate."""

    @classmethod
    def name(cls):
        return "facebook"

    def __init__(self, messenger_client: MessengerClient) -> None:

        self.messenger_client = messenger_client
        self.token = MongoTokenStore("endpoints.yml")
        super(MessengerBot, self).__init__()

    def set_access_token(self, page_id: Text) -> None:
        page_access_token = self.token.retrieve(page_id)
        self.messenger_client.set_page_access_token(page_access_token)

    def send_action_typing_on(self, recipient_id: Text, page_id: Text) -> None:

        self.set_access_token(page_id)
        self.messenger_client.send_action(
            "typing_on", {"sender": {"id": recipient_id}})

    def send_payload(self, recipient_id: Text, page_id: Text, payload: Dict[Text, Any]) -> None:

        self.set_access_token(page_id)
        self.messenger_client.send(payload,
                                   {"sender": {"id": recipient_id}},
                                   'RESPONSE')

    def send(self, recipient_id: Text, page_id: Text, element: Any) -> None:
        """Sends a message to the recipient using the messenger client."""

        # this is a bit hacky, but the client doesn't have a proper API to
        # send messages but instead expects the incoming sender to be present
        # which we don't have as it is stored in the input channel.

        self.set_access_token(page_id)
        self.messenger_client.send(element.to_dict(),
                                   {"sender": {"id": recipient_id}},
                                   'RESPONSE')

    def send_text_message(self, recipient_id: Text, page_id: Text, message: Text) -> None:
        """Send a message through this channel."""

        logger.info("Sending message to {0}: {1}".format(page_id, message))

        for message_part in message.split("\n\n"):
            self.send_action_typing_on(recipient_id, page_id)
            self.send(recipient_id, page_id, FBText(text=message_part))

    def send_image_url(self, recipient_id: Text, page_id: Text, image_url: Text) -> None:
        """Sends an image. Default will just post the url as a string."""

        self.send(recipient_id, page_id, attachments.Image(url=image_url))

    def send_text_with_buttons(self, recipient_id: Text, page_id: Text, text: Text,
                               buttons: List[Dict[Text, Any]],
                               **kwargs: Any) -> None:
        """Sends buttons to the output."""

        # buttons is a list of tuples: [(option_name,payload)]
        if len(buttons) > 3:
            logger.warning(
                "Facebook API currently allows only up to 3 buttons. "
                "If you add more, all will be ignored.")
            self.send_text_message(recipient_id, page_id, text)
        else:
            self._add_postback_info(buttons)
            messages = text.split("\n\n")
            text = messages.pop()

            for message in messages:
                self.send_text_message(recipient_id, page_id, message)

            self.send_action_typing_on(recipient_id, page_id)

            # Currently there is no predefined way to create a message with
            # buttons in the fbmessenger framework - so we need to create the
            # payload on our own
            payload = {
                "attachment": {
                    "type": "template",
                    "payload": {
                        "template_type": "button",
                        "text": text,
                        "buttons": buttons
                    }
                }
            }
            self.send_payload(recipient_id, page_id, payload)

    def send_custom_message(self, recipient_id: Text, page_id: Text,
                            elements: List[Dict[Text, Any]]) -> None:
        """Sends elements to the output."""

        for element in elements:
            self._add_postback_info(element['buttons'])

        payload = {
            "attachment": {
                "type": "template",
                "payload": {
                    "template_type": "generic",
                    "elements": elements
                }
            }
        }
        self.messenger_client.send(payload,
                                   self._recipient_json(recipient_id),
                                   'RESPONSE')

    @staticmethod
    def _add_postback_info(buttons: List[Dict[Text, Any]]) -> None:
        """Make sure every button has a type. Modifications happen in place."""
        for button in buttons:
            if 'type' not in button:
                button['type'] = "postback"

    @staticmethod
    def _recipient_json(recipient_id: Text) -> Dict[Text, Dict[Text, Text]]:
        """Generate the response json for the recipient expected by FB."""
        return {"sender": {"id": recipient_id}}


class FacebookInput(InputChannel):
    """Facebook input channel implementation. Based on the HTTPInputChannel."""

    @classmethod
    def name(cls):
        return "facebook"

    @classmethod
    def from_credentials(cls, credentials):
        if not credentials:
            cls.raise_missing_credentials_exception()

        return cls(credentials.get("verify"),
                   credentials.get("secret"),
                   credentials.get("page-access-token"))

    def __init__(self, fb_verify: Text, fb_secret: Text,
                 fb_access_token: Text) -> None:
        """Create a facebook input channel.

        Needs a couple of settings to properly authenticate and validate
        messages. Details to setup:

        https://github.com/rehabstudio/fbmessenger#facebook-app-setup

        Args:
            fb_verify: FB Verification string
                (can be chosen by yourself on webhook creation)
            fb_secret: facebook application secret
            fb_access_token: access token to post in the name of the FB page
        """
        self.fb_verify = fb_verify
        self.fb_secret = fb_secret
        self.fb_access_token = fb_access_token
        self.token = MongoTokenStore("endpoints.yml")
        self.content = ContentStore("endpoints.yml")

    def blueprint(self, on_new_message):

        fb_webhook = Blueprint('fb_webhook', __name__,
                               template_folder="fb-login", static_folder="fb-login/static")

        @fb_webhook.route("/", methods=['GET'])
        def health():
            return jsonify({"status": "ok"})

        @fb_webhook.route("/webhook", methods=['GET'])
        def token_verification():
            if request.args.get("hub.verify_token") == self.fb_verify:
                return request.args.get("hub.challenge")
            else:
                logger.warning(
                    "Invalid fb verify token! Make sure this matches "
                    "your webhook settings on the facebook app.")
                return "failure, invalid token"

        @fb_webhook.route("/webhook", methods=['POST'])
        def webhook():
            signature = request.headers.get("X-Hub-Signature") or ''
            if not self.validate_hub_signature(self.fb_secret, request.data,
                                               signature):
                logger.warning("Wrong fb secret! Make sure this matches the "
                               "secret in your facebook app settings")
                return "not validated"

            messenger = Messenger(self.fb_access_token, on_new_message)

            messenger.handle(request.get_json(force=True))

            return "success"

        @fb_webhook.route("/login", methods=['GET'])
        def login():
            try:
                return render_template("index.html")
            except:
                return "Not found" + os.getcwd()

        @fb_webhook.route("/subscribe", methods=['POST'])
        def subscribe_app():
            data = request.get_data()
            data = data.decode('utf-8')
            logger.info(data)
            request_params = parse_qs(data)
            self.token.get_pages().update_one(
                {"page_id": request_params['page_id'][0]},
                {"$set": {"page_name": request_params['page_name'][0],
                          "page_admin_id": request_params['page_admin_id'][0],
                          "page_access_token": request_params["page_access_token"][0], "page_persistent_menu": [],
                          "page_secret": self.fb_secret, "page_verify": self.fb_verify}},
                upsert=True
            )
            answer_inserted = self.content.init_answers(request_params['page_id'][0])
            logger.info(answer_inserted)
            return jsonify({"status": "success"})

        @fb_webhook.route("/subscribe", methods=['DELETE'])
        def unsubscribe_app():
            data = request.get_data()
            data = data.decode('utf-8')
            request_params = parse_qs(data)
            self.token.get_pages().delete_one(
                {"page_id": request_params['page_id'][0]})
            self.content.del_answers(request_params['page_id'][0])
            return jsonify({"status": "success"})
            
        return fb_webhook

    @staticmethod
    def validate_hub_signature(app_secret, request_payload,
                               hub_signature_header):
        """Make sure the incoming webhook requests are properly signed.

        Args:
            app_secret: Secret Key for application
            request_payload: request body
            hub_signature_header: X-Hub-Signature header sent with request

        Returns:
            bool: indicated that hub signature is validated
        """

        # noinspection PyBroadException
        try:
            hash_method, hub_signature = hub_signature_header.split('=')
        except Exception:
            pass
        else:
            digest_module = getattr(hashlib, hash_method)
            hmac_object = hmac.new(
                bytearray(app_secret, 'utf8'),
                request_payload, digest_module)
            generated_hash = hmac_object.hexdigest()
            if hub_signature == generated_hash:
                return True
        return False
