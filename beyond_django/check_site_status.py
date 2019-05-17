import requests
import time
import warnings
from django.core.mail import mail_admins
from django_project.private_settings import JOIN_API_KEY

warnings.filterwarnings("ignore") # Suppress all warnings, including the InsecureRequestWarning caused by verify=False below

time.sleep(900) # Give some time to the server to ready itself before starting to check if it works

new_status_code = 200 # Set the intial status to that of a working website

while True:
    old_status_code = new_status_code
    # new_status_code = requests.get('https://imbc2.imb.uni-mainz.de:8443/', verify=False).status_code
    new_status_code = requests.get("https://127.0.0.1:8443/", verify=False).status_code
    if new_status_code != 200 and old_status_code == 200:
        mail_admins("The Ulrich intranet is down", "The Ulrich intranet is down", fail_silently=True)
        try:
            # Send push notification to Nicola via Join
            join_url = "https://joinjoaomgcd.appspot.com/_ah/api/messaging/v1/sendPush?deviceNames={deviceNames}&text={text}&title={title}&apikey={apikey}".format(
                deviceNames = "Home%20Spectre%2CIMB%20Envy%2CPixel%202",
                text = "The%20Ulrich%20Intranet%20is%20down",
                title = "The%20Ulrich%20Intranet%20is%20down",
                apikey = JOIN_API_KEY)
            notification = requests.get(join_url)
        except:
            pass
    time.sleep(900)