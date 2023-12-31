class SaveWithoutHistoricalRecord():

    def save_without_historical_record(self, *args, **kwargs):
        """Allows inheritance of a method to save an object without
        saving a historical record as described in  
        https://django-simple-history.readthedocs.io/en/2.7.2/querying_history.html?highlight=save_without_historical_record"""

        self.skip_history_when_saving = True
        try:
            ret = self.save(*args, **kwargs)
        finally:
            del self.skip_history_when_saving
        return ret