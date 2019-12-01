import inspect
from django.core.mail import send_mail
from django.contrib.auth.models import User
from django_project.private_settings import ALLOWED_HOSTS
from django_project.private_settings import SITE_TITLE
from django_project.private_settings import SERVER_EMAIL_ADDRESS
from django.urls import reverse
from record_approval.models import RecordToBeApproved

if RecordToBeApproved.objects.all().exists(): # Check if there are records to be be approved at all

    PI_USER = User.objects.get(labuser__is_principal_investigator=True)

    RECORD_APPROVAL_URL = reverse("admin:record_approval_recordtobeapproved_changelist")

    EMAIL_MESSAGE_TXT = inspect.cleandoc("""Dear {},

    Please visit https://{}{} to check for new or modified records that need to be approved.

    Best wishes,
    The {}
    """.format(PI_USER.first_name, ALLOWED_HOSTS[0], RECORD_APPROVAL_URL, SITE_TITLE))

    send_mail(
        "{} weekly notification".format(SITE_TITLE),
        EMAIL_MESSAGE_TXT,
        SERVER_EMAIL_ADDRESS,
        [PI_USER.email],
    )

# Delete all completed tasks 

from background_task.models_completed import CompletedTask
CompletedTask.objects.all().delete()

# Delete history items that differ just by last_changed_date_time 

from collection_management.models import Plasmid
from collection_management.models import SaCerevisiaeStrain
from collection_management.models import Oligo
from collection_management.models import ScPombeStrain
from collection_management.models import EColiStrain
from collection_management.models import CellLine
from collection_management.models import Antibody
from order_management.models import Order

from collection_management.models import HistoricalPlasmid
from collection_management.models import HistoricalSaCerevisiaeStrain
from collection_management.models import HistoricalOligo
from collection_management.models import HistoricalScPombeStrain
from collection_management.models import HistoricalEColiStrain
from collection_management.models import HistoricalCellLine
from collection_management.models import HistoricalAntibody
from order_management.models import HistoricalOrder

from datetime import timedelta
from django.utils import timezone

def delete_dup_hist_rec_ids(model, time_delta):
    """Delete history items that differ just by last_changed_date_time"""

    def pairwise(iterable):
        """ Create pairs of consecutive items from
        iterable"""

        import itertools
        a, b = itertools.tee(iterable)
        next(b, None)
        return zip(a, b)
    
    items_to_check = model.objects.filter(last_changed_date_time__gte=time_delta)

    hist_item_ids_delete = []

    for item in items_to_check:
        history_records = item.history.all()
        if history_records.count() > 1:
            history_pairs = pairwise(history_records)
            for history_element in history_pairs:
                
                newer_record = history_element[0]
                older_record = history_element[1]
                delta = newer_record.diff_against(older_record)
                changed_fields = delta.changed_fields
                if 'last_changed_date_time' in changed_fields and len(changed_fields)==1:
                    hist_item_ids_delete.append(delta.new_record.history_id)

    return(hist_item_ids_delete)

MODELS = {Plasmid: HistoricalPlasmid,
        SaCerevisiaeStrain: HistoricalSaCerevisiaeStrain,
        Oligo: HistoricalOligo,
        ScPombeStrain: HistoricalScPombeStrain,
        EColiStrain: HistoricalEColiStrain,
        CellLine: HistoricalCellLine,
        Antibody: HistoricalAntibody,
        Order: HistoricalOrder}

NOW_MINUS_8DAYS = timezone.now() - timedelta(days=8)

for model, history_model in MODELS.items():
    ids_to_delete = delete_dup_hist_rec_ids(model, NOW_MINUS_8DAYS)
    if ids_to_delete:
        history_model.objects.filter(history_id__in=ids_to_delete).delete()