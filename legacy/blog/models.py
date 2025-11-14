from django.db import models

class Post(models.Model):
    class Meta:
        ordering = ['-date']

    date = models.DateTimeField('Date', auto_now=True, null=False)
    author = models.CharField('Author', max_length=100, null=False)
    title = models.CharField('Title', max_length=100, null=False)
    text = models.TextField('Text', null=False)

    def __str__(self):
        return self.title
