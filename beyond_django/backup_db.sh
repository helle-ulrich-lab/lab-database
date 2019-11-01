#!/bin/bash

DATABASE_NAME='django'

# Dirs

FILE_DIR="$( cd "$( /usr/bin/dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && /bin/pwd )"
DJANGO_PROJECT_DIR=$(echo $FILE_DIR | rev | cut -d'/' -f2- | rev)
ENV_DIR=$(echo $FILE_DIR | rev | cut -d'/' -f3- | rev)
BACKUP_DIR=$DJANGO_PROJECT_DIR/db_backup

# Remove all and .gz files older than 7 days from backup folder 
/usr/bin/find $BACKUP_DIR/db_dumps/ -maxdepth 1 -type f -mtime +7 -iname '*.gz' -delete

# Create datadump for django database and gzip it
CURRENT_DATE_TIME=`date +'%Y%m%d_%H%M'`
/usr/bin/mysqldump -u django -p$MYSQL_DB_PASSWORD $DATABASE_NAME | gzip > $BACKUP_DIR/db_dumps/${CURRENT_DATE_TIME}.sql.gz

# Save db tables as Excel files
$ENV_DIR/bin/python $DJANGO_PROJECT_DIR/manage.py shell < $DJANGO_PROJECT_DIR/beyond_django/export_db_tables_as_xlsx.py

# Save wiki articles as markdown files
rm -r $BACKUP_DIR/wiki_articles/*
$ENV_DIR/bin/python $DJANGO_PROJECT_DIR/manage.py shell < $DJANGO_PROJECT_DIR/beyond_django/export_wiki_articles_as_md.py

# Sync uploads
/usr/bin/rsync -a $DJANGO_PROJECT_DIR/uploads/ $BACKUP_DIR/uploads