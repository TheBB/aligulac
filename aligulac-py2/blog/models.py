from django.db import models

class Post(models.Model):
    date = models.DateTimeField(auto_now=True)
    author = models.CharField(max_length=100)
    title = models.CharField(max_length=100)
    text = models.TextField()

    def __unicode__(self):
        return self.title
