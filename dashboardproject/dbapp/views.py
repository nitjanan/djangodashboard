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
    

def get_base_api(mode):
    b_api = BaseAPI.objects.get(apiname = "webstock")  # query เมื่อเรียกใช้งานจริง
    if mode == 1:
        return b_api.url
    if mode == 2:
        return b_api.username
    if mode == 3:
        return b_api.password
    
# -------------------------
# get access token
# -------------------------
def get_jwt_token():
    url = f"{get_base_api(1)}/jwt/create/"

    payload = {
        "username": get_base_api(2),
        "password": get_base_api(3)
    }

    res = requests.post(url, json=payload, timeout=10)
    res.raise_for_status()

    data = res.json()

    return data["access"], data["refresh"]

# -------------------------
# verify token
# -------------------------
def verify_token(token):
    url = f"{get_base_api(1)}/jwt/verify/"

    payload = {
        "token": token
    }

    res = requests.post(url, json=payload, timeout=10)

    return res.status_code == 200


# -------------------------
# refresh token
# -------------------------
def refresh_token(refresh):
    url = f"{get_base_api(1)}/jwt/refresh/"

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
    url = f"{get_base_api(1)}/all/car/department/api/between/{start_date}/{end_date}/"
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
        f"{get_base_api(1)}"
        f"/all/exp/repair/api/between/"
        f"2026-01-01/{today}/"
    )

    data_by_url = get_api_data(url)

    # ลบหลัง api success เท่านั้น กันข้อมูลซ้ำเมื่อกดซ้ำ
    deleteOldDataSummary("2026-01-01", today, SummaryRepair)

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

    url = f"{get_base_api(1)}/all/exp/oil/by/month/api/between/2026-01-01/{today}/"
    data_by_url = get_api_data(url)

    deleteOldDataSummary("2026-01-01", today, SummaryOil)

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


@transaction.atomic
def createWork():
    today = date.today()

    url = f"{get_base_api(1)}/all/exp/by/month/api/between/2026-01-01/{today}/"
    data_by_url = get_api_data(url)

    deleteOldDataSummary("2026-01-01", today, SummaryWork)

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


def build_car_table_rows(car_dep_id, year, company_in, selected_car_type_id):
    table_filter = {
        'car_dep_id': car_dep_id,
        'year': year,
        'branch_company_id__in': company_in,
        'car_id__isnull': False,
    }

    if selected_car_type_id != 'all':
        table_filter['car__car_type_id'] = selected_car_type_id

    rows = {}

    def ensure_row(item):
        key = (item['car_id'], item['branch_company_id'])

        if key not in rows:
            car_name = item.get('car__name') 

            rows[key] = {
                'car_id': item['car_id'],
                'branch_company_id': item['branch_company_id'],
                'branch_company_name': item.get('branch_company__name') or '',
                'code': item.get('car__code') or '',
                'name': car_name,
                'brand': car_name,
                'model': '-',
                'start_year': '-',
                'percent_ma': 0,
                'avg_work_per_day': 0,
                'work_total': 0,
                'oil_total': 0,
                'fuel_rate': 0,
                'repair_total': 0,
                'repair_cost_per_hr': 0,
            }

        return rows[key]

    repair_rows = (
        SummaryRepair.objects
        .filter(**table_filter)
        .values(
            'car_id',
            'car__code',
            'car__name',
            'branch_company_id',
            'branch_company__name',
        )
        .annotate(repair_total=Sum('amount'))
    )

    for item in repair_rows:
        row = ensure_row(item)
        row['repair_total'] = float(item['repair_total'] or 0)

    oil_rows = (
        SummaryOil.objects
        .filter(**table_filter)
        .values(
            'car_id',
            'car__code',
            'car__name',
            'branch_company_id',
            'branch_company__name',
        )
        .annotate(oil_total=Sum('sum_liter'))
    )

    for item in oil_rows:
        row = ensure_row(item)
        row['oil_total'] = float(item['oil_total'] or 0)

    work_rows = (
        SummaryWork.objects
        .filter(**table_filter)
        .values(
            'car_id',
            'car__code',
            'car__name',
            'branch_company_id',
            'branch_company__name',
            'car_dep',
        )
        .annotate(
            work_total=Sum('sum_diff_mile'),
            work_days=Sum('count_diff_time'),
        )
    )

    for item in work_rows:
        row = ensure_row(item)
        work_total = float(item['work_total'] or 0)
        work_days = float(item['work_days'] or 0)
        car_dep_value = calByCarDep(item.get('car_dep'))

        if work_days > 0:
            row['avg_work_per_day'] = work_total / work_days

        if work_total > 0:
            row['fuel_rate'] = row['oil_total'] / work_total
            row['repair_cost_per_hr'] = row['repair_total'] / work_total

        if work_days > 0 and car_dep_value > 0:
            row['percent_ma'] = (work_total / (work_days * car_dep_value)) * 100

        row['work_total'] = work_total

    table_rows = sorted(rows.values(), key=lambda row: (row['code'], row['branch_company_name']))
    work_total_sum = sum(row['work_total'] for row in table_rows)
    oil_total_sum = sum(row['oil_total'] for row in table_rows)
    repair_total_sum = sum(row['repair_total'] for row in table_rows)
    percent_values = [row['percent_ma'] for row in table_rows if row['percent_ma'] > 0]
    avg_work_values = [row['avg_work_per_day'] for row in table_rows if row['avg_work_per_day'] > 0]

    table_totals = {
        'percent_ma': sum(percent_values) / len(percent_values) if percent_values else 0,
        'avg_work_per_day': sum(avg_work_values) / len(avg_work_values) if avg_work_values else 0,
        'work_total': work_total_sum,
        'oil_total': oil_total_sum,
        'fuel_rate': oil_total_sum / work_total_sum if work_total_sum > 0 else 0,
        'repair_total': repair_total_sum,
        'repair_cost_per_hr': repair_total_sum / work_total_sum if work_total_sum > 0 else 0,
    }

    return table_rows, table_totals


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
    selected_car_type_id = request.GET.get('car_type_id', 'all')
    if selected_car_type_id != 'all' and not selected_car_type_id.isdigit():
        selected_car_type_id = 'all'
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

    car_type_ids = set()
    car_type_base_filter = {
        'car_dep_id': car_dep_id,
        'year': '2026',
        'branch_company_id__in': company_in,
        'car__car_type_id__isnull': False,
    }

    for model in (SummaryRepair, SummaryOil, SummaryWork):
        car_type_ids.update(
            model.objects
            .filter(**car_type_base_filter)
            .values_list('car__car_type_id', flat=True)
            .distinct()
        )

    car_types = BaseCarType.objects.filter(id__in=car_type_ids)
    available_car_type_ids = {str(car_type.id) for car_type in car_types}

    if selected_car_type_id != 'all' and selected_car_type_id not in available_car_type_ids:
        selected_car_type_id = 'all'

    car_table_rows, car_table_totals = build_car_table_rows(
        car_dep_id,
        '2026',
        company_in,
        selected_car_type_id
    )

    base_filter = {
        'car_dep_id': car_dep_id,
        'year': '2026'
    }

    if selected_car_type_id != 'all':
        base_filter['car__car_type_id'] = selected_car_type_id

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
            'selected_car_type_id': selected_car_type_id,
            'cat': cat, 'car_types': car_types, 'car_by_dep': car_by_dep, 'car_code': car_code,
            'car_table_rows': car_table_rows, 'car_table_totals': car_table_totals,
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

    # summary มี FK ไป base ต้องโหลด base ก่อน
    updateOrCreateExpBaseCarType()
    updateOrCreateExpBaseRepairType()
    updateOrCreateExpBaseCarDepartment()
    updateOrCreateExpBaseCar()

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
        f"{get_base_api(1)}"
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
        f"{get_base_api(1)}"
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
        f"{get_base_api(1)}"
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
    car_type_id = request.GET.get('car_type_id', 'all')
    request.session['car_dep_id'] = car_dep_id

    if car_type_id != 'all' and car_type_id.isdigit():
        return redirect(f"{reverse('home')}?car_type_id={car_type_id}")

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

    url = f"{get_base_api(1)}/exp/basecartype/api/"

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

    url = f"{get_base_api(1)}/exp/baserepairtype/api/"

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

    url = f"{get_base_api(1)}/exp/basecardepartment/api/"

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

    url = f"{get_base_api(1)}/exp/basecar/api/"

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
                        'code': item.get('code'),
                        'name': item['name'],
                        'car_dep_id': item['car_dep'],
                        'car_type_id': item['car_type'],
                    }
                )

        except Exception as e:

            print(f"ERROR : {e}")

    return True
