from django.shortcuts import redirect, render

from django.contrib import auth, messages
from django.contrib.auth import (authenticate, login, logout,
                                 update_session_auth_hash)
from django.contrib.auth.decorators import login_required

# Create your views here.


@login_required(login_url='login')
def cadastros_assistenciais(request):

    if request.user.is_authenticated:
        return render(request, 'cadastros_assistenciais/cadastros_assistenciais.html')
    else:
        return redirect('login')
