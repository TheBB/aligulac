from django.db import models

class Post(models.Model):
    class Meta:
        ordering = ['index']

    title = models.CharField('Title', max_length=100, null=False)
    text = models.TextField('Text', null=False)
    index = models.IntegerField('Index', null=False)

    def __str__(self):
        return self.title
