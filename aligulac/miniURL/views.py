# Create your views here.

#-*- coding: utf-8 -*-
from django.shortcuts import redirect, get_object_or_404, render
from models import MiniURL
from forms import MiniURLForm
 
 
def list(request):
    """Print all redirects"""
    minis = MiniURL.objects.order_by('-nb_access')
 
    return render(request, 'miniURL/list.html', locals())
 
 
def new(request):
    """Add a redirect"""
    if request.method == "POST":
        form = MiniURLForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect(list)
    else:
        form = MiniURLForm()
 
    return render(request, 'miniURL/new.html', {'form':form})
 
 
def redirect(request, code):
    """Redirect to the registered URL"""
    mini = get_object_or_404(MiniURL, code=code)
    mini.nb_access += 1
    mini.save()
 
    return redirect(miniURL, permanent=True)
