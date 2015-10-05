import os
import requests

INSTAGRAM_CLIENT_ID = os.environ['INSTAGRAM_CLIENT_ID']
INSTAGRAM_CLIENT_SECRET = os.environ['INSTAGRAM_CLIENT_SECRET']
SERVER_URL = os.environ['SERVER_URL']


if __name__ == '__main__':
    response = requests.get(
        "https://api.instagram.com/v1/subscriptions?client_secret={SECRET}&client_id={ID}"
        .format(SECRET=INSTAGRAM_CLIENT_SECRET, ID=INSTAGRAM_CLIENT_ID)
    )
    if not response.json().get('data'):
        response = requests.post(
            "https://api.instagram.com/v1/subscriptions/",
            data=dict(
                client_id=INSTAGRAM_CLIENT_ID,
                client_secret=INSTAGRAM_CLIENT_SECRET,
                object="user",
                aspect="media",
                verify_token="TOKENOFDOOM",
                callback_url=SERVER_URL + "/realtime_callback",
            )
        )
        if response.ok:
            print "done"
        else:
            print "failed", response.status_code
    else:
        print "exists"


