import inspect
from django.core.mail import send_mail
from django.urls import reverse
from approval.models import RecordToBeApproved

from django.conf import settings
SITE_TITLE = getattr(settings, 'SITE_TITLE', 'Lab DB')
ALLOWED_HOSTS = getattr(settings, 'ALLOWED_HOSTS', [])
SERVER_EMAIL_ADDRESS = getattr(settings, 'SERVER_EMAIL_ADDRESS', 'noreply@example.com')


def get_formz_project_leader_emails(qs):

    """Returns the user ids of the project leaders for a queryset of
    relevant approval objects"""

    from django.contrib.auth.models import User

    qs = qs.exclude(content_type__model__in=['order', 'oligo'])

    ids = []

    for approval_obj in qs:
        project_leader_ids = list(approval_obj.content_object.formz_projects.all().values_list('project_leader', flat=True))
        ids.extend(project_leader_ids)

    pi_user_id = User.objects.get(labuser__is_principal_investigator=True).id
    
    if pi_user_id not in ids:
        ids.append(pi_user_id)
    
    project_leader_emails = User.objects.filter(id__in=ids).values_list('email', flat=True)

    return list(project_leader_emails)

RECORDS_TO_BE_APPROVED = RecordToBeApproved.objects.all()

if RECORDS_TO_BE_APPROVED.exists(): # Check if there are records to be be approved at all

    PROJECT_LEADER_EMAILS = get_formz_project_leader_emails(RECORDS_TO_BE_APPROVED)
    APPROVAL_URL = reverse("admin:approval_recordtobeapproved_changelist")
    EMAIL_MESSAGE_TXT = inspect.cleandoc("""Hello there,

    There are records that need your approval.

    You can visit https://{}{} to check for new or modified records that need to be approved.

    Best wishes,
    The {}
    """.format(ALLOWED_HOSTS[0], APPROVAL_URL, SITE_TITLE))

    send_mail(
        "{} weekly notification".format(SITE_TITLE),
        EMAIL_MESSAGE_TXT,
        SERVER_EMAIL_ADDRESS,
        PROJECT_LEADER_EMAILS,
    )

# Delete all completed tasks 

from background_task.models import CompletedTask
CompletedTask.objects.all().delete()

# Delete history items that differ just by last_changed_date_time 

from collection.models.plasmid import Plasmid
from collection.models.sa_cerevisiae_strain import SaCerevisiaeStrain
from collection.models.oligo import Oligo
from collection.models.sc_pombe_strain import ScPombeStrain
from collection.models.e_coli_strain import EColiStrain
from collection.models.cell_line import CellLine
from collection.models.antibody import Antibody
from collection.models.worm_strain import WormStrain
from ordering.models import Order

from collection.models import HistoricalPlasmid
from collection.models import HistoricalSaCerevisiaeStrain
from collection.models import HistoricalOligo
from collection.models import HistoricalScPombeStrain
from collection.models import HistoricalEColiStrain
from collection.models import HistoricalCellLine
from collection.models import HistoricalAntibody
from collection.models import HistoricalWormStrain
from ordering.models import HistoricalOrder

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
        WormStrain: HistoricalWormStrain,
        Order: HistoricalOrder}

NOW_MINUS_8DAYS = timezone.now() - timedelta(days=8)

for model, history_model in MODELS.items():
    ids_to_delete = delete_dup_hist_rec_ids(model, NOW_MINUS_8DAYS)
    if ids_to_delete:
        history_model.objects.filter(history_id__in=ids_to_delete).delete()