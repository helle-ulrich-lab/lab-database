#! /bin/bash

# Dirs

FILE_DIR="$( cd "$( /usr/bin/dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && /bin/pwd )"
DJANGO_PROJECT_DIR=$(echo $FILE_DIR | rev | cut -d'/' -f2- | rev)
ENV_DIR=$(echo $FILE_DIR | rev | cut -d'/' -f3- | rev)

$ENV_DIR/bin/python $DJANGO_PROJECT_DIR/manage.py shell < $DJANGO_PROJECT_DIR/extras/check_site_status.py