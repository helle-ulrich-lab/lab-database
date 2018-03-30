#!/bin/bash

# Set PATH varibale, necessary when running script from chrontab
PATH=/usr/bin:/bin

# Absolute path to backup folder
BACKUP_DIR=/home/nzilio/ulrich_lab_intranet_db_backup

# List of database tables to backup
DB_TABLE_LIST="auth_user
collection_management_antibody
collection_management_ecolistrain
collection_management_huplasmid
collection_management_mammalianline
collection_management_nzplasmid
collection_management_oligo
collection_management_sacerevisiaestrain
collection_management_scpombestrain"

# List of database tables to clean up
DB_HISTORY_CLEANUP_TABLE_LIST="collection_management_historicalhuplasmid
collection_management_historicalnzplasmid"

# Clean up duplicates from plasmid history tables
# Duplicates produced by calling the save method twice when uploading a plasmid map,
# to rename it 
for ENTRY in ${DB_HISTORY_CLEANUP_TABLE_LIST[@]};
do
mysql --user="django" --password="dFf3CpE8yqpVzadIn5VJ" --database="django" \
--execute="DELETE FROM $ENTRY WHERE plasmid_map LIKE '%temp%'; \
DELETE a FROM $ENTRY a LEFT JOIN(SELECT MAX(history_date) maxtimestamp, id, \
name, other_name, parent_vector, selection, us_e, construction_feature, \
received_from, note, reference, plasmid_map, created_by_id, history_user_id \
FROM $ENTRY GROUP BY id, name, other_name, parent_vector, selection, us_e, \
construction_feature, received_from, note, reference, plasmid_map, created_by_id, \
history_user_id ) b ON a.history_date = maxtimestamp AND a.id = b.id AND \
a.name = b.name AND a.other_name = b.other_name AND a.parent_vector = \
b.parent_vector AND a.selection = b.selection AND a.us_e = b.us_e AND \
a.construction_feature = b.construction_feature AND a.received_from = \
b.received_from AND a.note = b.note AND a.reference = b.reference AND \
a.plasmid_map = b.plasmid_map AND a.created_by_id = b.created_by_id AND \
a.history_user_id = b.history_user_id WHERE b.maxtimestamp IS NULL; \
UPDATE $ENTRY SET history_type = '+' WHERE ABS(UNIX_TIMESTAMP(created_date_time) \
- UNIX_TIMESTAMP(last_changed_date_time)) < 0.25;"
done

# Clean up duplicates from antibody history tables
mysql --user="django" --password="dFf3CpE8yqpVzadIn5VJ" --database="django" \
--execute="
DELETE FROM collection_management_historicalantibody WHERE info_sheet LIKE '%temp%'; \
DELETE a FROM collection_management_historicalantibody a LEFT JOIN(SELECT MAX(history_date) maxtimestamp, \
id, name, species_isotype, clone, received_from, catalogue_number, l_ocation, a_pplication, \
description_comment, info_sheet, created_by_id, history_user_id \
FROM collection_management_historicalantibody GROUP BY id, name, species_isotype, clone, \
received_from, catalogue_number, l_ocation, a_pplication, description_comment, info_sheet, \
created_by_id, history_user_id ) b ON a.history_date = maxtimestamp AND a.id = b.id AND \
a.name = b.name AND a.species_isotype = b.species_isotype AND a.clone = b.clone AND \
a.received_from = b.received_from AND a.catalogue_number = b.catalogue_number AND \
a.l_ocation = b.l_ocation AND a.a_pplication = b.a_pplication AND a.description_comment = b.description_comment AND \
a.info_sheet = b.info_sheet AND a.created_by_id = b.created_by_id AND \
a.history_user_id = b.history_user_id WHERE b.maxtimestamp IS NULL; \
UPDATE collection_management_historicalantibody SET history_type = '+' WHERE ABS(UNIX_TIMESTAMP(created_date_time) \
- UNIX_TIMESTAMP(last_changed_date_time)) < 0.25;"

# Remove all .tab and .gz files from backup folder 
rm -rf $BACKUP_DIR/*.{tab,gz}

# Create datadump for django database and gzip it
mysqldump -u django -pdFf3CpE8yqpVzadIn5VJ django | gzip > $BACKUP_DIR/ulrich_lab_intranet_db_dump.sql.gz

# Export specific database tables as tab-delimited text files
for ENTRY in ${DB_TABLE_LIST[@]};
do
mysql -u django -pdFf3CpE8yqpVzadIn5VJ --column-names=TRUE django -e "SELECT * from "$ENTRY";" > $BACKUP_DIR/$ENTRY.tab
# Get rid of all non-end-of-line whitespaces from the exported tables
sed -i ':a;N;$!ba;s/\r/ /g' $BACKUP_DIR/$ENTRY.tab
sed -i ':a;N;$!ba;s/ *\\n/ /g' $BACKUP_DIR/$ENTRY.tab
done

# Set absolute path to root of the Ulrich Intranet virtual environment
ULRICH_INTRA_ENV=/home/nzilio/ulrich_lab_intranet
# Run gspread_to_autocomplete_json.py with Python executable from the Ulrich Intranet virtual environment
$ULRICH_INTRA_ENV/bin/python $ULRICH_INTRA_ENV/django_project/beyond_django/gspread_to_autocomplete_json.py