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
from django.db.models import Q, Sum, IntegerField, Min, Max, F, FloatField, Value, Case, When
from django.db.models.functions import Coalesce, Concat
from django.db.models.expressions import ExpressionWrapper
from dateutil.relativedelta import relativedelta
from django.db import transaction

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
def getDataFromApiTest( url):
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        return data

    except Exception as e:
        return []
    
#API_BASE = "http://127.0.0.1:8000"
b_api = BaseAPI.objects.get(id = 1)
API_BASE = b_api.url

# -------------------------
# get access token
# -------------------------
def get_jwt_token():
    url = f"{API_BASE}/jwt/create/"

    payload = {
        "username": b_api.username,
        "password": b_api.password
    }

    res = requests.post(url, json=payload, timeout=10)
    res.raise_for_status()

    data = res.json()

    return data["access"], data["refresh"]

# -------------------------
# verify token
# -------------------------
def verify_token(token):
    url = f"{API_BASE}/jwt/verify/"

    payload = {
        "token": token
    }

    res = requests.post(url, json=payload, timeout=10)

    return res.status_code == 200


# -------------------------
# refresh token
# -------------------------
def refresh_token(refresh):
    url = f"{API_BASE}/jwt/refresh/"

    payload = {
        "refresh": refresh
    }

    res = requests.post(url, json=payload, timeout=10)
    res.raise_for_status()

    data = res.json()

    return data["access"]


# -------------------------
# call protected api
# -------------------------
def get_api_data(api_url):
    try:
        access, refresh = get_jwt_token()

        headers = {
            "Authorization": f"Bearer {access}"
        }

        all_results = []
        next_url = api_url

        while next_url:
            res = requests.get(next_url, headers=headers, timeout=10)

            # token expired
            if res.status_code == 401:
                new_access = refresh_token(refresh)

                headers = {
                    "Authorization": f"Bearer {new_access}"
                }

                res = requests.get(next_url, headers=headers, timeout=10)

            res.raise_for_status()

            data = res.json()

            # ถ้ามี pagination
            if isinstance(data, dict) and "results" in data:
                all_results.extend(data["results"])
                next_url = data["next"]   # page ถัดไป
            else:
                return data

        return all_results

    except Exception as e:
        print("JWT ERROR =", e)
        return []


def findCompanyIn(request):
    code = request.session['company_code']

    #หาหน้าต่างการมองเห็นบริษัททั้งหมดของ user
    user_profile = UserProfile.objects.get(user = request.user.id)
    company_all = BaseBranchCompany.objects.filter(userprofile = user_profile).values('id')

    if code == "ALL":
        company_in = company_all
    else:
        company_in = BaseBranchCompany.objects.filter(code = code).values('id')
        
    return company_in

def updateOrCreateSummaryCarDep(start_date, end_date):
    url = f"{API_BASE}/all/car/department/api/between/{start_date}/{end_date}/"
    car_by_dep = get_api_data(url)

    for item in car_by_dep:
        SummaryCarDep.objects.update_or_create(
            ext_id=item['id'],
            branch_company_id=item['branch_company'],
            defaults={
                'code': item['code'],
                'name': item['name'],
                'car_dep_id': item['car_dep'],
            }
        )

@transaction.atomic
def createRepair():
    today = date.today()
    url = (
        f"{API_BASE}"
        f"/all/exp/repair/api/between/"
        f"2026-01-01/{today}/"
    )

    data_by_url = get_api_data(url)
    objs = []
    for item in data_by_url:

        objs.append(
            SummaryRepair(
                branch_company_id=item['branch_company'],
                summary_date=date(
                    int(item['year']),
                    int(item['month']),
                    1
                ),
                month=int(item['month']),
                year=int(item['year']),
                month_th=item['month_th'],
                repair_name=item['rt_name'],
                amount=item['amount'],
                car_id=item['car_id'],
                car_code=item['car_code'],
                repair_id=item['note2'],
                car_dep_id=item['car_dep'],
            )
        )

    # insert ทีเดียว
    SummaryRepair.objects.bulk_create(
        objs,
        batch_size=1000
    )

    return True

@transaction.atomic
def createOil():
    today = date.today()

    url = f"{API_BASE}/all/exp/oil/by/month/api/between/2026-01-01/{today}/"
    data_by_url = get_api_data(url)

    objs = []
    for item in data_by_url:
        objs.append(
            SummaryOil(
                branch_company_id = item['branch_company'],
                # วันที่ 1 ของเดือน
                summary_date=date(
                    int(item['year']),
                    int(item['month']),
                    1
                ),
                month  =  item['month'],
                year = item['year'],
                month_th = item['month_th'],

                car_dep_id = item['car_dep'],
                car_id = item['car_id'],

                sum_liter = item['sum_liter'],
                sum_km = item['sum_km'],
                liter_per_km = item['liter_per_km'],
            )
        )
        # insert ทีเดียว
    SummaryOil.objects.bulk_create(
        objs,
        batch_size=1000
    )

    return True


def createWork():
    today = date.today()

    url = f"{API_BASE}/all/exp/by/month/api/between/2026-01-01/{today}/"
    data_by_url = get_api_data(url)

    objs = []
    for item in data_by_url:
        objs.append(
            SummaryWork(
                branch_company_id = item['branch_company'],
                # วันที่ 1 ของเดือน
                summary_date=date(
                    int(item['year']),
                    int(item['month']),
                    1
                ),
                month  =  item['month'],
                year = item['year'],
                month_th = item['month_th'],

                car_dep_id = item['car_dep'],
                car_id = item['car_id'],

                sum_diff_mile = item['sum_diff_mile'],
                count_diff_time = item['count_diff_time'],
                percent = item['percent'],
            )
        )
            
    # insert ทีเดียว
    SummaryWork.objects.bulk_create(
        objs,
        batch_size=1000
    )
    return True

def calByCarDep(car_dep):
    # 🔧 ปรับตามจริงของคุณ
    if str(car_dep) == "2":   # รถบรรทุก/ยานพาหนะ
        return 35
    elif str(car_dep) == "3": # เครื่องจักรกลหนัก
        return 10
    return 8


# เดือนทั้งหมด
all_months = [
    'มกราคม', 'กุมภาพันธ์', 'มีนาคม', 'เมษายน',
    'พฤษภาคม', 'มิถุนายน', 'กรกฎาคม', 'สิงหาคม',
    'กันยายน', 'ตุลาคม', 'พฤศจิกายน', 'ธันวาคม'
]

@login_required(login_url='login')
def home(request):
    try:
        #active : active คือแท็ปบริษัท active
        active = request.session['company_code']
        company_in = findCompanyIn(request)
        comp = BaseBranchCompany.objects.get(code = active)
    except:
        return redirect('logout')

    car_dep_id = request.session.get('car_dep_id', '1')    
    # get from URL only
    car_code = request.GET.get('car_code', 'null')
    branch_company_id = request.GET.get('branch_company_id')

    # เดือนปัจจุบัน
    current_month = datetime.now().month

    #today = date.today()
    #url = f"{API_BASE}/baseCarDepartment/api/all"
    #url_carbydep = f"{API_BASE}/car/department/api/between/2026-01-01/{today}/{comp.affiliated.name}/{car_dep_id}/"
    #url_repair = f"{API_BASE}/exp/repair/api/between/2026-01-01/{today}/{comp.code}/{car_dep_id}/"
    #url_cartype = f"{API_BASE}/exp/cartype/api/between/2026-01-01/{today}/{comp.affiliated.name}/{car_dep_id}/"
    #url_bymonth = f"{API_BASE}/exp/by/month/api/between/2026-01-01/{today}/{comp.affiliated.name}/{car_dep_id}/"
    #url_oilbymonth = f"{API_BASE}/exp/oil/by/month/api/between/2026-01-01/{today}/{comp.affiliated.name}/{car_dep_id}/"
    #url_workbymonth = f"{API_BASE}/exp/work/by/month/api/between/2026-01-01/{today}/{comp.code}/{car_dep_id}/"

    #cat = get_api_data(url)
    #car_by_dep = get_api_data(url_carbydep)
    #repair = get_api_data(url_repair)
    #bymonth = get_api_data(url_bymonth)
    #cartype = get_api_data(url_cartype)
    #oilbymonth = get_api_data(url_oilbymonth)
    #workbymonth = get_api_data(url_workbymonth)

    cat  = BaseCarDepartment.objects.filter(~Q(id = 4))
    car_by_dep = SummaryCarDep.objects.filter(branch_company_id__in = company_in, car_dep_id = car_dep_id)


    base_filter = {
        'car_dep_id': car_dep_id,
        'year': '2026'
    }

    # selected car
    if car_code != 'null' and branch_company_id:

        base_filter['car__code'] = car_code
        base_filter['branch_company_id'] = branch_company_id

    # normal company tab
    else:

        base_filter['branch_company_id__in'] = company_in


    repair = (
        SummaryRepair.objects
        .filter(**base_filter)
        .values('repair_name')
        .annotate(amount_sum=Sum('amount'))
        .order_by('-amount_sum')
    )

    bymonth = (
        SummaryRepair.objects
        .filter(**base_filter)
        .values('month', 'month_th')
        .annotate(amount_sum=Sum('amount'))
        .order_by('month')
    )

    cartype = (
        SummaryRepair.objects
        .filter(**base_filter)
        .values('car__car_type__name')
        .annotate(amount_sum=Sum('amount'))
        .order_by('-amount_sum')
    )

    oilbymonth = (
        SummaryOil.objects
        .filter(**base_filter)
        .values('month', 'month_th')
        .annotate(
            sum_liter_sum=Coalesce(
                Sum('sum_liter'),
                Value(0),
                output_field=FloatField()
            ),
            sum_km_sum=Coalesce(
                Sum('sum_km'),
                Value(0),
                output_field=FloatField()
            ),
        )
        .annotate(
            real_liter_per_km=Case(
                When(sum_km_sum=0, then=Value(0.0)),
                default=ExpressionWrapper(
                    F('sum_liter_sum') / F('sum_km_sum'),
                    output_field=FloatField()
                ),
                output_field=FloatField()
            )
        )
        .order_by('month')
    )

    workbymonth = list(
        SummaryWork.objects
        .filter(**base_filter)
        .values('month', 'month_th', 'car_dep')
        .annotate(
            total_mile=Coalesce(
                Sum('sum_diff_mile'),
                Value(0),
                output_field=FloatField()
            ),
            total_time=Coalesce(
                Sum('count_diff_time'),
                Value(0),
                output_field=FloatField()
            ),
        )
        .order_by('month')
    )

    expbycar = (
        SummaryRepair.objects
        .filter(**base_filter)
        .annotate(
            car_name_code=Concat('car__name', Value(':'), 'car__code')
        )
        .values('car_name_code')
        .annotate(amount_sum=Sum('amount'))
        .order_by('-amount_sum')
    )


    # queryset -> dict
    repair_dict = {
        str(item['month']).zfill(2): float(item['amount_sum'] or 0)
        for item in bymonth
    }

    work_dict = {
        str(item['month']).zfill(2): float(item['total_mile'] or 0)
        for item in workbymonth
    }

    # labels เดือน 1 -> เดือนปัจจุบัน
    repair_work_labels = [
        all_months[i - 1]
        for i in range(1, current_month + 1)
    ]

    # data เดือน 1 -> เดือนปัจจุบัน
    repair_work_data1 = [
        repair_dict.get(f"{i:02d}", 0)
        for i in range(1, current_month + 1)
    ]

    repair_work_data2 = [
        work_dict.get(f"{i:02d}", 0)
        for i in range(1, current_month + 1)
    ]

    repair_series = [float(r['amount_sum']) or 0 for r in repair]
    repair_labels = [ r['repair_name'] if r['repair_name'] else 'ไม่ระบุ' for r in repair]
    repair_total = sum(repair_series)

    car_type_series = [float(r['amount_sum']) for r in cartype]
    car_type_labels = [r['car__car_type__name'] if r['car__car_type__name'] else 'ไม่ระบุ' for r in cartype]
    car_type_total = sum(car_type_series)


    bymonth_series = [float(r['amount_sum']) for r in bymonth]
    bymonth_labels = [r['month_th'] if r['month_th'] else 'ไม่ระบุ' for r in bymonth]

    oilbymonth_data1 = [float(r['sum_liter_sum']) for r in oilbymonth]
    oilbymonth_data2 = [float(r['real_liter_per_km'] or 0) for r in oilbymonth]
    oilbymonth_labels = [r['month_th'] if r['month_th'] else 'ไม่ระบุ' for r in oilbymonth]

    workbymonth_data1 = []
    workbymonth_data2 = []
    workbymonth_labels = []

    for item in workbymonth:
        total_mile = float(item.get('total_mile', 0))
        total_time = float(item.get('total_time', 0))
        car_dep = item.get('car_dep', 0)

        car_value = calByCarDep(car_dep)

        percent = 0

        if total_time > 0 and car_value > 0:
            percent = (
                total_mile /
                (total_time * car_value)
            ) * 100

        workbymonth_data1.append(round(total_mile, 2))
        workbymonth_data2.append(round(percent, 2))
        workbymonth_labels.append(
            item['month_th'] if item['month_th'] else 'ไม่ระบุ'
        )

    expbycar_series = [float(r['amount_sum']) for r in expbycar]
    expbycar_labels = [r['car_name_code'] if r['car_name_code'] else 'ไม่ระบุ' for r in expbycar]
    expbycar_total = sum(expbycar_series)

    return render(
        request,"index.html", 
        {   'selected_car_dep_id': car_dep_id,
            'cat': cat, 'car_by_dep': car_by_dep, 'car_code': car_code,
            'repair_series': repair_series, 'repair_labels': repair_labels, 'repair_total': repair_total,
            'car_type_series': car_type_series, 'car_type_labels': car_type_labels, 'car_type_total': car_type_total,
            'bymonth_series': bymonth_series, 'bymonth_labels': bymonth_labels,
            'oilbymonth_data1': oilbymonth_data1, 'oilbymonth_data2': oilbymonth_data2 , 'oilbymonth_labels': oilbymonth_labels,
            'workbymonth_data1': workbymonth_data1, 'workbymonth_data2': workbymonth_data2 , 'workbymonth_labels': workbymonth_labels,
            'expbycar_series': expbycar_series, 'expbycar_labels': expbycar_labels, 'expbycar_total': expbycar_total,
            'repair_work_data1': repair_work_data1, 'repair_work_data2': repair_work_data2 , 'repair_work_labels': repair_work_labels,
            active :"active",
            'tab_mt' : "active",
        })

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
                #CPT*เลือกตามบริษัท 
                try:
                    user_profile = UserProfile.objects.get(user = request.user.id)
                    company = BaseBranchCompany.objects.filter(userprofile = user_profile).first()
                except:
                    company = BaseBranchCompany.objects.get(id = 1)
                request.session['company_code'] = company.code
                request.session['company'] = company.name

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
        #CPT*เลือกตามบริษัท 
        company = BaseBranchCompany.objects.first()
        request.session['company_code'] = company.code
        request.session['company'] = company.name
        
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

def updateValueAPI(request):
    today = date.today()
    start_in_year =  "2026-01-01"

    updateOrCreateSummaryCarDep(start_in_year, today)
    createRepair()
    createOil()
    createWork()
    return redirect('home')

def update_summary_from_api(request):
    today = date.today()
    try:
        # ย้อนหลัง 3 เดือน
        start_date = (today - relativedelta(months=3)).replace(day=1)
        end_date = today
        updateDataSummary(start_date, end_date)
        return HttpResponse("update summary from api success")
    
    except Exception as e:
        print(e)
        return HttpResponse(f"error : {e}", status=500)

def updateDataSummary(start_date, end_date):
    updateOrCreateSummaryCarDep(start_date, end_date)
    updateOrCreateRepair(start_date, end_date)
    updateOrCreateOil(start_date, end_date)
    updateOrCreateWork(start_date, end_date)
    return True

def deleteOldDataSummary(start_date, end_date, modelName):
    modelName.objects.filter(
        summary_date__range=(
            start_date,
            end_date
        )
    ).delete()

@transaction.atomic
def updateOrCreateRepair(start_date, end_date):
    url = (
        f"{API_BASE}"
        f"/all/exp/repair/api/between/"
        f"{start_date}/{end_date}/"
    )

    try:
        # call api ก่อน
        data_by_url = get_api_data(url)
    except Exception as e:
        print(f"API ERROR : {e}")
        # JWT error / 500 error
        return False

    # ถ้า api ไม่มีข้อมูล
    if not data_by_url:
        print("API EMPTY")
        return False

    # delete หลัง api success เท่านั้น
    deleteOldDataSummary(start_date, end_date, SummaryRepair)

    objs = []
    for item in data_by_url:
        objs.append(
            SummaryRepair(
                branch_company_id=item['branch_company'],
                month=int(item['month']),
                year=int(item['year']),
                summary_date=date(
                    int(item['year']),
                    int(item['month']),
                    1
                ),
                month_th=item['month_th'],
                repair_name=item['rt_name'],
                amount=item['amount'],
                car_id=item['car_id'],
                car_code=item['car_code'],
                repair_id=item['note2'],
                car_dep_id=item['car_dep'],
            )
        )

    SummaryRepair.objects.bulk_create(
        objs,
        batch_size=1000
    )

    return True

@transaction.atomic
def updateOrCreateOil(start_date, end_date):
    url = (
        f"{API_BASE}"
        f"/all/exp/oil/by/month/api/between/"
        f"{start_date}/{end_date}/"
    )

    try:
        # call api ก่อน
        data_by_url = get_api_data(url)
    except Exception as e:
        print(f"API ERROR : {e}")
        # JWT error / 500 error
        return False

    # ถ้า api ไม่มีข้อมูล
    if not data_by_url:
        print("API EMPTY")
        return False

    # delete หลัง api success เท่านั้น
    deleteOldDataSummary(start_date, end_date, SummaryOil)

    objs = []
    for item in data_by_url:
        objs.append(
            SummaryOil(
                branch_company_id=item['branch_company'],
                month=item['month'],
                year=item['year'],
                # วันที่ 1 ของเดือน
                summary_date=date(
                    int(item['year']),
                    int(item['month']),
                    1
                ),
                month_th=item['month_th'],
                car_dep_id = item['car_dep'],
                car_id = item['car_id'],
                sum_liter = item['sum_liter'],
                sum_km = item['sum_km'],
                liter_per_km = item['liter_per_km'],
            )
        )

    SummaryOil.objects.bulk_create(
        objs,
        batch_size=1000
    )
    return True

@transaction.atomic
def updateOrCreateWork(start_date, end_date):
    url = (
        f"{API_BASE}"
        f"/all/exp/by/month/api/between/"
        f"{start_date}/{end_date}/"
    )
    try:
        # call api ก่อน
        data_by_url = get_api_data(url)
    except Exception as e:
        print(f"API ERROR : {e}")
        # JWT error / 500 error
        return False

    # ถ้า api ไม่มีข้อมูล
    if not data_by_url:
        print("API EMPTY")
        return False

    # delete หลัง api success เท่านั้น
    deleteOldDataSummary(start_date, end_date, SummaryWork)

    objs = []
    for item in data_by_url:
        objs.append(
            SummaryWork(
                branch_company_id=item['branch_company'],
                month=item['month'],
                year=item['year'],
                # วันที่ 1 ของเดือน
                summary_date=date(
                    int(item['year']),
                    int(item['month']),
                    1
                ),
                month_th = item['month_th'],
                car_dep_id = item['car_dep'],
                car_id = item['car_id'],
                sum_diff_mile = item['sum_diff_mile'],
                count_diff_time = item['count_diff_time'],
                percent = item['percent'],
            )
        )

    SummaryWork.objects.bulk_create(
        objs,
        batch_size=1000
    )
    return True

def setSessionCompany(request):
    name = request.GET.get('title', None)
    request.session['company_code'] = name
    company = BaseBranchCompany.objects.get(code = request.session['company_code'])
    request.session['company'] = company.affiliated.name_sh

    # clear car filter
    request.session.pop('car_code', None)

    data = {
        'instance': request.session['company_code'],
    }
    return JsonResponse(data)

def getApiDataToDashbord(request):
    car_dep_id = request.GET.get('car_dep_id', '1')
    request.session['car_dep_id'] = car_dep_id
    return redirect('home')

def update_base_from_api(request):
    try:
        updateOrCreateExpBaseCarType()
        updateOrCreateExpBaseRepairType()
        updateOrCreateExpBaseCarDepartment()
        updateOrCreateExpBaseCar()
        return HttpResponse("update base from api success")
    
    except Exception as e:
        print(e)
        return HttpResponse(f"error : {e}", status=500)
    
from django.db import transaction


def updateOrCreateExpBaseCarType():

    url = f"{API_BASE}/exp/basecartype/api/"

    try:
        data_by_url = get_api_data(url)

    except Exception as e:
        print(f"API ERROR : {e}")
        return False

    if not data_by_url:
        return False

    for item in data_by_url:

        try:

            with transaction.atomic():

                BaseCarType.objects.update_or_create(
                    id=item['id'],
                    defaults={
                        'name': item['name']
                    }
                )

        except Exception as e:

            print(f"ERROR : {e}")

    return True


def updateOrCreateExpBaseRepairType():

    url = f"{API_BASE}/exp/baserepairtype/api/"

    try:
        data_by_url = get_api_data(url)

    except Exception as e:
        print(f"API ERROR : {e}")
        return False

    if not data_by_url:
        return False

    for item in data_by_url:

        try:

            with transaction.atomic():

                BaseRepairType.objects.update_or_create(
                    id=item['id'],
                    defaults={
                        'name': item['name']
                    }
                )

        except Exception as e:

            print(f"ERROR : {e}")

    return True


def updateOrCreateExpBaseCarDepartment():

    url = f"{API_BASE}/exp/basecardepartment/api/"

    try:
        data_by_url = get_api_data(url)

    except Exception as e:
        print(f"API ERROR : {e}")
        return False

    if not data_by_url:
        return False

    for item in data_by_url:

        try:

            with transaction.atomic():

                BaseCarDepartment.objects.update_or_create(
                    id=item['id'],
                    defaults={
                        'name': item['name']
                    }
                )

        except Exception as e:

            print(f"ERROR : {e}")

    return True


def updateOrCreateExpBaseCar():

    url = f"{API_BASE}/exp/basecar/api/"

    try:
        data_by_url = get_api_data(url)

    except Exception as e:
        print(f"API ERROR : {e}")
        return False

    if not data_by_url:
        return False

    for item in data_by_url:

        try:

            with transaction.atomic():

                BaseCar.objects.update_or_create(
                    id=item['id'],
                    defaults={
                        'code': item['code'],
                        'name': item['name'],
                        'car_dep_id': item['car_dep'],
                        'car_type_id': item['car_id'],
                    }
                )

        except Exception as e:

            print(f"ERROR : {e}")

    return True