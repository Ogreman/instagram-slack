import os
import logging
import requests
import json
from flask import Flask, request, jsonify
from instagram import client, subscriptions

FORMAT = "%(asctime)-15s: %(levelname)s: %(message)s"
logging.basicConfig(format=FORMAT, filename="insta.log", level=logging.DEBUG)

app = Flask(__name__)
APP_TOKENS = [
    val
    for key, val in os.environ.items()
    if key.startswith('APP_TOKEN')
]
INSTAGRAM_CLIENT_ID = os.environ['INSTAGRAM_CLIENT_ID']
INSTAGRAM_CLIENT_SECRET = os.environ['INSTAGRAM_CLIENT_SECRET']
INSTAGRAM_AUTH_URL = "https://instagram.com/oauth/authorize/?client_id={CLIENT}&redirect_uri={REDIRECT}&response_type=token"
REALTIME_CALLBACK_URL = os.environ['SERVER_URL'] + "/realtime_callback"
OAUTH_CALLBACK_URL = os.environ['SERVER_URL'] + "/oauth_callback"
SLACK_WEB_URL = "https://hooks.slack.com/services" + os.environ['WEBHOOK_BITS']
POST_TEXT = "New post by <https://instagram.com/{user}|{user}>: {url}"


api = client.InstagramAPI(
    client_id=INSTAGRAM_CLIENT_ID, 
    client_secret=INSTAGRAM_CLIENT_SECRET
)


def process_user_update(update):
    logging.info(update)
    try:
        image = api.media(update['data']['media_id'])
        url = image.get_standard_resolution_url()
        requests.post(SLACK_WEB_URL, data=json.dumps(
            {'text': POST_TEXT.format(url=url, user=image.user)}
        ))
    except KeyError:
        logging.error('Missing media_id')
    except Exception as e:
        logging.exception(str(e))


reactor = subscriptions.SubscriptionsReactor()
reactor.register_callback(subscriptions.SubscriptionType.USER, process_user_update)


@app.route('/realtime_callback', methods=['GET', 'POST'])
def on_realtime_callback():
    mode = request.args.get("hub.mode")
    challenge = request.args.get("hub.challenge")
    verify_token = request.args.get("hub.verify_token")
    if challenge:
        logging.debug("Returned signature")
        return challenge
    else:
        x_hub_signature = request.headers.get('X-Hub-Signature')
        try:
            logging.debug("Processing!")
            reactor.process(INSTAGRAM_CLIENT_SECRET, request.data, x_hub_signature)
        except subscriptions.SubscriptionVerifyError:
            logging.error("Signature mismatch")
        return ''


@app.route('/oauth_callback')
def on_callback():
    try:
        access_token = request.url.split('access_token=')[0]
        if not access_token:
            logging.error('Could not get access token')
        client.InstagramAPI(
            access_token=access_token, 
            client_secret=INSTAGRAM_CLIENT_SECRET
        )
        return "Done"
    except Exception as e:
        logging.exception(str(e))
        return "Failed!"


def add_user():
    return "Authenticate here: {URL}".format(
        URL=INSTAGRAM_AUTH_URL.format(
            CLIENT=INSTAGRAM_CLIENT_ID,
            REDIRECT=OAUTH_CALLBACK_URL
        )
    )


def help_insta():
    return """
    Usage: `/insta COMMAND [ARGUMENTS]...`

    Commands:

      *register*   Register your account with the watchlist.
      *help*       Outputs this help text.
    
    Examples:
    
      _register example usage:_
        `/insta register`      


    Arguments:

      *register* 
        `/insta register`
    """


@app.route("/")
def index():
    return 'instadoom'


@app.route("/insta", methods=['POST'])
def insta():
    
    def get_args(request, func_name):
        return request.form['text'][len(func_name) + 1:]

    def get_func(func_name):
        return {
            'register': add_user,
            'help': help_insta,
        }[func_name]

    def get_fname(request):
        return request.form['text'].split(' ')[0]

    if request.form.get('token') in APP_TOKENS:
        try:
            fname = get_fname(request)
            function = get_func(fname)
            return function()
        except (ValueError, KeyError) as e:
            logging.exception(str(e))
            return "Error - expected: (command [text])"
    else:
        logging.error("invalid token: %s", request.form.get('token'))
    return "Nope :|"


if __name__ == "__main__":
    if os.environ.get('INSTA_PRODUCTION'):
        app.run(host='0.0.0.0', port=80, debug=os.environ.get('INSTA_DEBUG', False))
    else:
        app.run(debug=os.environ.get('INSTA_DEBUG', True))

