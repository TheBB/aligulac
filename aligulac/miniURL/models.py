from django.db import models
from django.contrib.auth.models import User

import random
import string

class MiniURL(models.Model):
    class Meta:
        verbose_name = "Mini URL"
        verbose_name_plural = "Mini URLs"
        db_table = 'miniurl'

    code = models.CharField('Code', max_length=16, primary_key=True)
    longURL = models.URLField('URL', unique=True, null=False)
    date = models.DateTimeField('Date', auto_now_add=True, null=False)
    submitter = models.ForeignKey(User, null=True, blank=True, verbose_name='Submitter')
    nb_access = models.PositiveIntegerField('# accessed', default=0, null=False)

    def __str__(self):
        return '[{0}] {1}'.format(self.code, self.longURL)

    def save(self, *args, **kwargs):
        if len(self.code) == 0:
            self.generate()
        super(MiniURL, self).save(*args, **kwargs)

    def generate(self, N=16):
        characters = string.ascii_letters + string.digits
        self.code = ''.join([random.choice(characters) for _ in range(N)])
