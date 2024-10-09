from django.forms import ValidationError


class InfoSheetMaxSizeMixin:

    def clean(self):

        errors = []
        file_size_limit = 2 * 1024 * 1024

        if self.info_sheet:

            # Check if file is bigger than 2 MB
            if self.info_sheet.size > file_size_limit:
                errors.append("File too large. Size cannot exceed 2 MB.")

            # Check if file's extension is '.pdf'
            try:
                info_sheet_ext = self.info_sheet.name.split(".")[-1].lower()
            except:
                info_sheet_ext = None
            if info_sheet_ext == None or info_sheet_ext != "pdf":
                errors.append("Invalid file format. Please select a valid .pdf file")

        if len(errors) > 0:
            raise ValidationError({"info_sheet": errors})
