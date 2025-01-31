from djangoql.schema import DjangoQLSchema, StrField

from .models import MsdsForm


class MsdsFormSearchFieldLabel(StrField):
    name = "file_name"
    model = MsdsForm
    model_fieldname = "label"
    suggest_options = True
    limit_options = 10

    def get_options(self, search):
        filter_search = {f"{self.model_fieldname}__icontains": search}
        if len(search) < 3:
            return ["Type 3 or more characters to see suggestions"]
        else:
            records = (
                self.model.objects.filter(**filter_search)
                .distinct()
                .order_by("label")[: self.limit_options]
            )
            return [r.file_name_description for r in records]

    def get_lookup_value(self, value):
        return value.replace(" ", "_")

    def get_lookup_name(self):
        return self.model_fieldname


class MsdsFormQLSchema(DjangoQLSchema):
    def get_fields(self, model):
        if model == MsdsForm:
            return ["id", MsdsFormSearchFieldLabel()]
        return super().get_fields(model)
