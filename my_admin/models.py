from django.db import models

class GeneralSetting (models.Model):
    
    order_email_addresses = models.EmailField("order email address", help_text='Email address to send urgent order notifications', blank=False)
    saveris_username = models.CharField("saveris username", max_length=255, blank=False)
    saveris_password = models.CharField("saveris password", max_length=255, blank=False)
    join_api_key = models.CharField("join api key", max_length=255, blank=True)
    ms_teams_webhook = models.URLField("MS Teams webhook", max_length=500, blank=True)

    class Meta:        
        verbose_name = 'general setting'
        verbose_name_plural = 'general settings'
    
    def __str__(self):
        return str(self.id)

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        
        # Remove any leading and trailing white spaces
        self.saveris_username = self.saveris_username.strip()
        self.saveris_password = self.saveris_password.strip()
        self.join_api_key = self.join_api_key.strip()
        
        super(GeneralSetting, self).save(force_insert, force_update, using, update_fields)
