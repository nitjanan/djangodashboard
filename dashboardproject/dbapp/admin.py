from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from import_export import fields, resources
from import_export.widgets import ForeignKeyWidget
from django.forms import CheckboxSelectMultiple, MultipleChoiceField, widgets
from django.db import models
from dbapp.models import BaseAffiliatedCompany, BaseAffiliatedCompany, BaseBranchCompany, BaseVisible, UserProfile, BaseCarType, BaseCarDepartment, BaseCar, BaseRepairType, BaseAPI, SummaryCarDep, SummaryRepair, SummaryOil, SummaryWork
from dbapp.forms import BaseCarAdminForm

# Register your models here.
class BaseAffiliatedCompanyAdmin(ImportExportModelAdmin):
    list_display = ['id','name','name_th'] #แสดงรายการสินค้าในรูปแบบตาราง
    list_per_page = 20 #แสดงผล 20 รายการต่อ 1 หน้า

class BaseBranchCompanyAdmin(ImportExportModelAdmin):
    list_display = ['id','code','affiliated', 'name'] #แสดงรายการสินค้าในรูปแบบตาราง
    list_per_page = 20 #แสดงผล 20 รายการต่อ 1 หน้า
	
class BaseVisibleAdmin(ImportExportModelAdmin):
    list_display = ('name',)
	
	
class UserProfileAdmin(ImportExportModelAdmin):
    formfield_overrides = {
        models.ManyToManyField: {'widget': CheckboxSelectMultiple},
    }
    autocomplete_fields = ['user']

    list_display = ['user'] #แสดงรายการสินค้าในรูปแบบตาราง
    list_per_page = 20 #แสดงผล 20 รายการต่อ 1 หน้า
    search_fields = ['user__first_name']

    class Media:
        js = ('dbapp/js/select_all.js',)

class BaseCarTypeAdmin(ImportExportModelAdmin):
    list_display = ['id','name'] #แสดงรายการสินค้าในรูปแบบตาราง
    search_fields = ['name',]

class BaseCarDepartmentAdmin(ImportExportModelAdmin):
    list_display = ['id','name'] #แสดงรายการสินค้าในรูปแบบตาราง
    search_fields = ['name',]
	

class BaseCarAdmin(ImportExportModelAdmin):
    autocomplete_fields = ['car_type',]

    list_display = ['id','code','name', 'car_dep', 'car_type']#แสดงรายการสินค้าในรูปแบบตาราง
    search_fields = ['code', 'name', 'car_type__name', 'car_dep__name']
    form = BaseCarAdminForm

class BaseRepairTypeAdmin(ImportExportModelAdmin):
    list_display = ['id','name'] #แสดงรายการสินค้าในรูปแบบตาราง
    search_fields = ['name']

class BaseAPIAdmin(ImportExportModelAdmin):
    list_display = ['id','url','apiname','username', 'password'] #แสดงรายการสินค้าในรูปแบบตาราง
    list_per_page = 20 #แสดงผล 20 รายการต่อ 1 หน้า

class SummaryCarDepAdmin(ImportExportModelAdmin):
    list_display = ['id','ext_id','code','name','branch_company','car_dep','v_stamp']
    list_filter = ['branch_company','car_dep']
    search_fields = ['code','name']
    list_per_page = 20 #แสดงผล 20 รายการต่อ 1 หน้า

class SummaryRepairAdmin(ImportExportModelAdmin):
    list_display = ['id','summary_date','year','month_th','repair_id','repair_name','amount','branch_company','car_dep','car_code']
    list_filter = ['year','month','branch_company','car_dep']
    search_fields = ['repair_name','car_code','car__name']
    list_per_page = 20 #แสดงผล 20 รายการต่อ 1 หน้า

class SummaryOilAdmin(ImportExportModelAdmin):
    list_display = ['id','summary_date','year','month_th','sum_liter','sum_km','liter_per_km','branch_company','car_dep','car']
    list_filter = ['year','month','branch_company','car_dep']
    search_fields = ['car__code','car__name']
    list_per_page = 20 #แสดงผล 20 รายการต่อ 1 หน้า

class SummaryWorkAdmin(ImportExportModelAdmin):
    list_display = ['id','summary_date','year','month_th','sum_diff_mile','count_diff_time','percent','branch_company','car_dep','car']
    list_filter = ['year','month','branch_company','car_dep']
    search_fields = ['car__code','car__name']
    list_per_page = 20 #แสดงผล 20 รายการต่อ 1 หน้า

admin.site.register(BaseAffiliatedCompany, BaseAffiliatedCompanyAdmin)
admin.site.register(BaseBranchCompany, BaseBranchCompanyAdmin)
admin.site.register(BaseVisible, BaseVisibleAdmin)
admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(BaseCarType, BaseCarTypeAdmin)
admin.site.register(BaseCarDepartment, BaseCarDepartmentAdmin)
admin.site.register(BaseCar, BaseCarAdmin)
admin.site.register(BaseRepairType, BaseRepairTypeAdmin)
admin.site.register(BaseAPI, BaseAPIAdmin)
admin.site.register(SummaryCarDep, SummaryCarDepAdmin)
admin.site.register(SummaryRepair, SummaryRepairAdmin)
admin.site.register(SummaryOil, SummaryOilAdmin)
admin.site.register(SummaryWork, SummaryWorkAdmin)