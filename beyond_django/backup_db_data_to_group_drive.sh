#!/bin/bash

DJANGO_BASE_DIR=/home/nzilio/ulrich_lab_intranet/django_project
BACKUP_DIR=$DJANGO_BASE_DIR/ulrich_lab_intranet_db_backup

# Remove all and .gz files older than 7 days from backup folder 
/usr/bin/find $BACKUP_DIR/db_dumps/ -maxdepth 1 -type f -mtime +7 -iname '*.gz' -delete

# Create datadump for django database and gzip it
CURRENT_DATE_TIME=`date +'%Y%m%d_%H%M'`
/usr/bin/mysqldump -u django -pdFf3CpE8yqpVzadIn5VJ django | gzip > $BACKUP_DIR/db_dumps/ulrich_lab_intranet_db_dump_${CURRENT_DATE_TIME}.sql.gz

/home/nzilio/ulrich_lab_intranet/bin/python $DJANGO_BASE_DIR/manage.py shell < $DJANGO_BASE_DIR/beyond_django/export_db_tables_as_xlsx.py

/home/nzilio/ulrich_lab_intranet/bin/python $DJANGO_BASE_DIR/manage.py shell < $DJANGO_BASE_DIR/beyond_django/export_wiki_articles_as_md.py

/usr/bin/rsync -a /home/nzilio/ulrich_lab_intranet/django_project/uploads/ /home/nzilio/ulrich_lab_intranet/django_project/ulrich_lab_intranet_db_backup/uploads
