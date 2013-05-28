#-*- coding: utf-8 -*-
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
        return u"[{0}] {1}".format(self.code, self.url)
    
    def save(self, *args, **kwargs):
        if self.pk is None:
            self.generate(16)
        super(MiniURL, self).save(*args, **kwargs)
        
    def generate(self, N):
        caracters = string.letters + string.digits
        random = [random.choice(caracters) for _ in xrange(N)]
 
        self.code = ''.join(random)
        
    class Meta:
        verbose_name = "Mini URL"
        verbose_name_plural = "Mini URLs"
    