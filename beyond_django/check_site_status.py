import requests
import time
import warnings
from django.core.mail import mail_admins
from django_project.private_settings import SITE_TITLE
from django_project.private_settings import ALLOWED_HOSTS

from my_admin.models import GeneralSetting

warnings.filterwarnings("ignore") # Suppress all warnings, including the InsecureRequestWarning caused by verify=False below

time.sleep(900) # Give some time to the server to ready itself before starting to check if it works

new_status_code = 200 # Set the intial status to that of a working website

while True:
    old_status_code = new_status_code
    new_status_code = requests.get("https://{}".format(ALLOWED_HOSTS[0]), verify=False).status_code
    
    if new_status_code != 200 and old_status_code == 200:
        
        mail_admins("The {} is down".format(SITE_TITLE), "The {} is down".format(SITE_TITLE), fail_silently=True)
        
        try:
            general_setting = GeneralSetting.objects.all().first()

            if general_setting.join_api_key:
                try:
                    # Send push notification to Nicola via Join
                    join_url = "https://joinjoaomgcd.appspot.com/_ah/api/messaging/v1/sendPush?deviceNames={deviceNames}&text={text}&title={title}&apikey={apikey}".format(
                        deviceNames = "Home%20Spectre%2CIMB%20Envy%2CPixel%202",
                        text = "The {} is down".format(SITE_TITLE).replace(' ', '%20'),
                        title = "The {} is down".format(SITE_TITLE).replace(' ', '%20'),
                        apikey = general_setting.join_api_key)
                    notification = requests.get(join_url)
                except:
                    pass
        except:
            pass
    time.sleep(900)