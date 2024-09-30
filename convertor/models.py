from django.db import models

class PowerPoint(models.Model):
    name = models.CharField(max_length=200)
    file = models.FileField(upload_to='uploads/ppt_files/')


# Create your models here.
