from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect, StreamingHttpResponse
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.conf import settings
from django.core.mail import EmailMessage
from django.utils import timezone
from django.urls import reverse
from .models import *
from datetime import date, timedelta, datetime, time
import calendar
import requests

#หาวันแรกของเดือนนี้
def startDateInMonth(day):
    dt = datetime.strptime(f"{day}", '%Y-%m-%d')
    result = dt.replace(day=1).date()
    return f"{result}"

#หาวันสุดท้ายของเดือนนี้
def endDateInMonth(day):
    dt = datetime.strptime(f"{day}", '%Y-%m-%d')
    day = calendar.monthrange(dt.year, dt.month)[1]
    result = dt.replace(day=day).date()
    return f"{result}"

# Create your views here.
@login_required(login_url='login')
def home(request):
    url = "http://localhost:3000/categories"
    url_repair = "http://localhost:3000/repair"

    try:
        response = requests.get(url, timeout=5)
        cat = response.json()
    except:
        cat = []

    try:
        response = requests.get(url_repair, timeout=5)
        repair = response.json()
    except:
        repair = []

    series = [r['amount'] for r in repair]
    labels = [r['rt_name'] if r['rt_name'] else 'ไม่ระบุ' for r in repair]

    return render(request,"index.html", {'cat': cat, 'series': series, 'labels': labels})

@login_required(login_url='login')
def about(request):
    return HttpResponse("about")

def LoginView(request):
    if request.method == 'POST':
        form = AuthenticationForm(data = request.POST)
        if form.is_valid():
            username = request.POST['username']
            password = request.POST['password']
            user = authenticate(username=username,password=password)
            #ถ้าล็อกอินสำเร็จไปหน้า home else ให้ไปสมัครใหม่
            if user is not None:
                login(request, user)

                #set session date in dashbord
                current_date_time = datetime.today()
                previous_date_time = current_date_time - timedelta(days=1)

                start_date = datetime.strptime(startDateInMonth(str(previous_date_time.strftime('%Y-%m-%d'))), "%Y-%m-%d")
                end_date = datetime.strptime(endDateInMonth(str(previous_date_time.strftime('%Y-%m-%d'))), "%Y-%m-%d")

                request.session['db_start_date'] = f'{start_date.strftime("%Y-%m-%d")}'
                request.session['db_end_date'] = f'{end_date.strftime("%Y-%m-%d")}'


                # ewdirect to home page
                return redirect('home')
            else:
                # redirect back to the login page if credentials are wrong
                messages.error(request, 'Invalid username or password')
                return redirect('login')
    else:
        form = AuthenticationForm()
        
    return render(request, 'account/login.html', {'form': form})

def LogoutView(request):

    logout(request)
    # redirect to login page after logout
    return redirect('login')

def setDateInDashbord(request):
    db_start_date = request.GET.get('db_start_date', None)
    db_end_date = request.GET.get('db_end_date', None)

    request.session['db_start_date'] = db_start_date
    request.session['db_end_date'] = db_end_date

    data = {
        'db_start_date' : db_start_date,
        'db_end_date' : db_end_date,
    }
    return JsonResponse(data)
