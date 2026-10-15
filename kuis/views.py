from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def kuis_home(request):
    return render(request, "kuis/index.html")