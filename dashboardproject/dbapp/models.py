from django.db import models
from django.contrib.auth.models import Group, User
from django.db.models.fields.related import ForeignKey

# Create your models here.
def get_first_name(self):
    return self.first_name + " " + self.last_name
User.add_to_class("__str__", get_first_name)


class BaseAPI(models.Model):
    url = models.CharField(max_length=255, blank=True, null = True, verbose_name="url api data")
    apiname = models.CharField(max_length=255, blank=True, null = True, verbose_name="api name")
    username = models.CharField(max_length=255, blank=True, null = True, verbose_name="username get api")
    password = models.CharField(max_length=255, blank=True, null = True, verbose_name="password get api")

    class Meta:
        db_table = 'base_api'
        ordering=('id',)
        verbose_name = 'ตั้งค่า API'
        verbose_name_plural = 'ข้อมูลตั้งค่า API'

    def __str__(self):
        return str(self.id)


class BaseAffiliatedCompany(models.Model):
    name = models.CharField(max_length=255,unique=True, verbose_name="โค้ดบริษัท")
    name_sh = models.CharField(max_length=255, blank=True, null = True, verbose_name="ชื่อบริษัทย่อ")
    name_th = models.CharField(max_length=255, blank=True, null = True, verbose_name="ชื่อบริษัทไทย")

    class Meta:
        db_table = 'BaseAffiliatedCompany'
        ordering=('id',)
        verbose_name = 'สังกัดบริษัท'
        verbose_name_plural = 'ข้อมูลสังกัดบริษัท'

    def __str__(self):
        return self.name


class BaseBranchCompany(models.Model):
    id = models.CharField(primary_key=True, max_length=255, unique=True, verbose_name="รหัสสาขาบริษัท")
    code = models.CharField(max_length=255,unique=True, verbose_name="โค้ดสาขาบริษัท")
    affiliated = models.ForeignKey(BaseAffiliatedCompany, on_delete=models.CASCADE, blank = True, null = True,related_name='branch_affiliated', verbose_name="ชื่อสังกัดบริษัท")
    name = models.CharField(max_length=255,unique=True, verbose_name="ชื่อสาขาบริษัท", blank = True, null = True)
    
    class Meta:
        db_table = 'BaseBranchCompany'
        ordering=('id',)
        verbose_name = 'สาขาบริษัท'
        verbose_name_plural = 'ข้อมูลสาขาบริษัท'

    def __str__(self):
        return self.name
	

class BaseVisible(models.Model):       
    name = models.CharField(max_length=255,unique=True, verbose_name="ชื่อแท็บการใช้งาน")

    class Meta:
        db_table = 'BaseVisible'
        ordering=('id',)
        verbose_name = 'แท็บการใช้งาน'
        verbose_name_plural = 'ข้อมูลแท็บการใช้งาน'
    
    def __str__(self):
        return str(self.name)
	
	
#USER PROFILE
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE,null=True, blank=True, verbose_name="ผู้ใช้")
    visible = models.ManyToManyField(BaseVisible,verbose_name="การมองเห็นแท็ปการใช้งาน")
    branch_company = models.ManyToManyField(BaseBranchCompany,verbose_name="การมองเห็นแท็ปบริษัท")

    class Meta:
        verbose_name = 'ผู้ใช้และตำแหน่งงาน'
        verbose_name_plural = 'ข้อมูลผู้ใช้และตำแหน่งงาน'

    def __str__(self):
        return self.user.username


class BaseCarType(models.Model):
    name = models.CharField(max_length=255,unique=True, verbose_name="ชื่อชนิดรถ/เครื่องจักร")

    class Meta:
        db_table = 'BaseCarType'
        ordering=('id',)
        verbose_name = 'ชนิดรถ/เครื่องจักร'
        verbose_name_plural = 'ข้อมูลชนิดรถ/เครื่องจักร'

    def __str__(self):
        return self.name

class BaseCarDepartment(models.Model):
    name = models.CharField(max_length=255,unique=True, verbose_name="ชื่อแผนกทะเบียนรถ/เครื่องจักร/หน่วยงาน")

    class Meta:
        db_table = 'BaseCarDepartment'
        ordering=('id',)
        verbose_name = 'แผนกทะเบียนรถ/เครื่องจักร/หน่วยงาน'
        verbose_name_plural = 'ข้อมูลแผนกทะเบียนรถ/เครื่องจักร/หน่วยงาน'
        indexes = [
			# search by name
			models.Index(
				fields=['name'],
				name='car_dep_name_idx'
			),
		]

    def __str__(self):
        return self.name

class BaseCar(models.Model):
    code = models.CharField(unique=True, max_length=255, blank=False, null=True, verbose_name="code")
    name = models.CharField(max_length=255, blank=False, null=True, verbose_name="ชื่อทะเบียนรถ/เครื่องจักร/หน่วยงาน")
    car_dep = models.ForeignKey(BaseCarDepartment,on_delete=models.CASCADE,null=True, blank=True, verbose_name="แผนกทะเบียนรถ/เครื่องจักร/หน่วยงาน")
    car_type = models.ForeignKey(BaseCarType,on_delete=models.CASCADE,null=True, blank=True, verbose_name="ชนิดรถ/เครื่องจักร")

    class Meta:
        db_table = 'BaseCar'
        ordering=('id',)
        verbose_name = 'ทะเบียนรถ/เครื่องจักร/หน่วยงาน'
        verbose_name_plural = 'ข้อมูลทะเบียนรถ/เครื่องจักร/หน่วยงาน'
        unique_together = 'name', 'code'
    
    def __str__(self):
        return str(self.name) + str(self.code)
    
class BaseRepairType(models.Model):
    id = models.CharField(primary_key=True, max_length=255, unique=True, verbose_name="รหัสประเภทการซ่อม")#เก็บประเภทการซ่อม
    name = models.CharField(max_length=255,unique=True, verbose_name="ชื่อประเภทการซ่อม")

    class Meta:
        db_table = 'BaseRepairType'
        ordering=('id',)
        verbose_name = 'ประเภทการซ่อม'
        verbose_name_plural = 'ข้อมูลประเภทการซ่อม'
    
    def __str__(self):
        return str(self.name)
    

class SummaryCarDep(models.Model):
    # id จากระบบต้นทาง
    ext_id = models.BigIntegerField(blank=False, null=True)

    code = models.CharField(
        max_length=20, blank=False, null=True
    )

    name = models.CharField(
        max_length=255, blank=False, null=True
    )

    branch_company = models.ForeignKey(BaseBranchCompany,on_delete=models.CASCADE,null=True, blank=True)

    car_dep = models.ForeignKey(
        BaseCarDepartment,
        on_delete=models.PROTECT,
        related_name='cars'
    )

    v_stamp = models.DateTimeField(
        auto_now=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:

        db_table = 'sum_car_dep'
        constraints = [

            models.UniqueConstraint(
                fields=[
                    'ext_id',
                    'branch_company'
                ],
                name='uniq_car_extid_branch'
            ),

        ]
        indexes = [

            # query branch + dep
            models.Index(
                fields=[
                    'branch_company',
                    'car_dep'
                ],
                name='car_branch_dep_idx'
            ),


            # dashboard lookup code
            models.Index(
                fields=[
                    'code'
                ],
                name='car_code_idx'
            ),

        ]

    def __str__(self):
        return f'{self.code} - {self.name}'
    

class SummaryRepair(models.Model):
    # ใช้แทน year + month สำหรับ query/filter
    summary_date = models.DateField(
        db_index=True,
        null=True,
        blank=True
    )

    year = models.IntegerField()
    month = models.IntegerField()
    month_th = models.CharField(
        max_length=20, blank=False, null=True
    )

    repair_id = models.CharField(
        max_length=10, blank=False, null=True
    )
    repair_name = models.CharField(
        max_length=255, blank=False, null=True
    )

    amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    branch_company = models.ForeignKey(BaseBranchCompany,on_delete=models.CASCADE,null=True, blank=True)
    car_dep = models.ForeignKey(
        BaseCarDepartment,
        on_delete=models.PROTECT,
        null=True, blank=True
    )

    car_code = models.CharField(
        max_length=20, blank=False, null=True
    )

    car = models.ForeignKey(
        BaseCar,
        on_delete=models.PROTECT,
        null=True, blank=True
    )

    v_stamp = models.DateTimeField(
        auto_now=True
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:

        db_table = 'sum_repair'
        indexes = [
            models.Index(
                fields=[
                    'summary_date'
                ],
                name='repair_summary_date_idx'
            ),
            # query branch + dep
            models.Index(
                fields=[
                    'branch_company',
                    'car_dep'
                ],
                name='repair_branch_dep_idx'
            ),
        ]

    def __str__(self):
        return f'{self.year}-{self.month}:{self.car}'
    

class SummaryOil(models.Model):
    # ใช้แทน year + month สำหรับ query/filter
    summary_date = models.DateField(
        db_index=True,
        null=True,
        blank=True
    )

    year = models.IntegerField()
    month = models.IntegerField()
    month_th = models.CharField(
        max_length=20, blank=False, null=True
    )
    sum_liter = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    sum_km = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    liter_per_km = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    branch_company = models.ForeignKey(BaseBranchCompany,on_delete=models.CASCADE,null=True, blank=True)
    car_dep = models.ForeignKey(
        BaseCarDepartment,
        on_delete=models.PROTECT,
        null=True, blank=True
    )

    car = models.ForeignKey(
        BaseCar,
        on_delete=models.PROTECT,
        null=True, blank=True
    )

    v_stamp = models.DateTimeField(
        auto_now=True
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:

        db_table = 'sum_oil'
        indexes = [
            models.Index(
                fields=[
                    'summary_date'
                ],
                name='oil_summary_date_idx'
            ),

            # query branch + dep
            models.Index(
                fields=[
                    'branch_company',
                    'car_dep'
                ],
                name='oil_branch_dep_idx'
            ),
        ]

    def __str__(self):
        return f'{self.year}-{self.month}:{self.car}'


class SummaryWork(models.Model):
    # ใช้แทน year + month สำหรับ query/filter
    summary_date = models.DateField(
        db_index=True,
        null=True,
        blank=True
    )

    year = models.IntegerField()
    month = models.IntegerField()
    month_th = models.CharField(
        max_length=20, blank=False, null=True
    )
    sum_diff_mile = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    count_diff_time = models.IntegerField()
    percent = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    branch_company = models.ForeignKey(BaseBranchCompany,on_delete=models.CASCADE,null=True, blank=True)
    car_dep = models.ForeignKey(
        BaseCarDepartment,
        on_delete=models.PROTECT,
        null=True, blank=True
    )

    car = models.ForeignKey(
        BaseCar,
        on_delete=models.PROTECT,
        null=True, blank=True
    )

    v_stamp = models.DateTimeField(
        auto_now=True
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:

        db_table = 'sum_work'
        indexes = [
            models.Index(
                fields=[
                    'summary_date'
                ],
                name='work_summary_date_idx'
            ),
            # query branch + dep
            models.Index(
                fields=[
                    'branch_company',
                    'car_dep'
                ],
                name='work_branch_dep_idx'
            ),
        ]

    def __str__(self):
        return f'{self.year}-{self.month}:{self.car}'


class SummaryMaintenance(models.Model):
    # ใบแจ้งซ่อมรายใบ จาก webstock (ใช้คำนวณ MTBF / MTTR)
    ext_id = models.BigIntegerField(unique=True)

    # ใช้แทน year + month สำหรับ query/filter (วันที่ 1 ของเดือนที่แจ้งซ่อม)
    summary_date = models.DateField(
        db_index=True,
        null=True,
        blank=True
    )

    year = models.IntegerField()
    month = models.IntegerField()

    reported_at = models.DateTimeField()  # วันเวลาแจ้งซ่อม (รถเสีย)
    finished_at = models.DateTimeField(null=True, blank=True)  # วันเวลาหัวหน้าช่างปิดงาน (ซ่อมเสร็จ)
    mile = models.IntegerField(null=True, blank=True)  # เลขไมล์/เลขชั่วโมง ตอนแจ้งซ่อม

    ma_type = models.CharField(  # 01 สั่งทำ, 02 ซ่อม, 03 ติดตั้ง, 04 ทำ PM
        max_length=10, blank=False, null=True
    )
    car_state = models.CharField(
        max_length=255, blank=False, null=True
    )
    is_complete = models.BooleanField(null=True, blank=True)

    branch_company = models.ForeignKey(BaseBranchCompany,on_delete=models.CASCADE,null=True, blank=True)
    car_dep = models.ForeignKey(
        BaseCarDepartment,
        on_delete=models.PROTECT,
        null=True, blank=True
    )

    car = models.ForeignKey(
        BaseCar,
        on_delete=models.PROTECT,
        null=True, blank=True
    )

    v_stamp = models.DateTimeField(
        auto_now=True
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:

        db_table = 'sum_maintenance'
        indexes = [
            models.Index(
                fields=[
                    'summary_date'
                ],
                name='ma_summary_date_idx'
            ),
            # query branch + dep
            models.Index(
                fields=[
                    'branch_company',
                    'car_dep'
                ],
                name='ma_branch_dep_idx'
            ),
        ]

    def __str__(self):
        return f'{self.ext_id}:{self.car}'