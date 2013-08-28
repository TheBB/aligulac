from django.db import models
from django.contrib.auth.models import User
import random
import string

# Create your models here.

class MiniURL(models.Model):
    code = models.CharField(max_length=16, primary_key=True)
    longURL = models.URLField(unique=True)
    date = models.DateTimeField(auto_now_add=True)
    submitter = models.ForeignKey(User, null=True, blank=True)
    nb_access = models.PositiveIntegerField(default=0)

    def __unicode__(self):
        return u"[{0}] {1}".format(self.code, self.longURL)

    def save(self, *args, **kwargs):
        if len(self.code) == 0:
            self.generate()
        super(MiniURL, self).save(*args, **kwargs)

    def generate(self, N=16):
        characters = string.letters + string.digits
        self.code = ''.join([random.choice(characters) for _ in xrange(N)])

    class Meta:
        verbose_name = "Mini URL"
        verbose_name_plural = "Mini URLs"

