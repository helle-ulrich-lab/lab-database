# Django-based web app for managing the lab collections and orders of the Ulrich lab @ IMB Mainz

This is a web app for managing the lab collections and 
orders of the Ulrich lab @ IMB Mainz. It is based on a heavily customised Django admin site.

If you want to use this app as is, you will need to set up a SnapGene server (free for academic use, see <https://www.snapgene.com/academics/snapgene-server/>) and include a file called private_settings.py in the django_project folder that contains the following variables (amend as appropriate!)

```python
# /django_project/private_settings.py
# Django settings

SECRET_KEY = 'example'
ALLOWED_HOSTS = ["example1",'example2'] # The first item should be the publicly accessible domain 
DB_NAME = 'example'
DB_USER = 'example'
DB_PASSWORD = 'example'
DEBUG = False
SERVER_EMAIL_ADDRESS = 'example'
SITE_ADMIN_EMAIL_ADDRESSES = [('name', 'email')]

# The title to show in the header and some email communication
SITE_TITLE = 'example'

# Abbreviation to be appended to files, e.g. HU for Helle Ulrich. Can be empty, like so ''
LAB_ABBREVIATION_FOR_FILES = 'example'
```