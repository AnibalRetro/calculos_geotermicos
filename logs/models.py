from django.db import models


class UploadedLAS(models.Model):
    file = models.FileField(upload_to='las_files/')
    original_name = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.original_name
