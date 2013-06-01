#-*- coding: utf-8 -*-

from django import forms
from models import MiniURL
 
class MiniURLForm(forms.ModelForm):
    class Meta:
        model = MiniURL
        fields = ('longURL','submitter')