from django.db import models

class Post(models.Model):
    title = models.CharField(max_length=100)
    text = models.TextField()
    index = models.IntegerField()

    def __unicode__(self):
        return self.title
