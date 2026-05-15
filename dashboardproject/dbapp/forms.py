
from django import forms
import string
from dbapp.models import  BaseCar


def has_only_en(name):
    char_set = string.ascii_letters + string.digits + "-"
    return all((True if x in char_set else False for x in name))

class BaseCarAdminForm(forms.ModelForm):
    class Meta:
        model = BaseCar
        fields = '__all__'

    def clean(self):
        cleaned_data = self.cleaned_data
        #ลบช่องว่างหน้าและหลัง
        code = cleaned_data.get('code').strip() if cleaned_data.get('code') else ''
        name = cleaned_data.get('name').strip() if cleaned_data.get('name') else ''
        
        hoen = has_only_en(code)

        if not hoen: #เช็คตัวอักษรภาษาไทยในรหัส
            raise forms.ValidationError(u"code เครื่องจักร/ทะเบียนรถ/หน่วยงาน ผิด ("+ str(code) +") มีตัวอักษรภาษาไทย ไม่สามารถบันทึกได้ กรุณาใส่รหัสสินค้าใหม่")
        if not code.isupper():  #เช็คตัวอักษรพิมใหญ่
            raise forms.ValidationError(u"code เครื่องจักร/ทะเบียนรถ/หน่วยงาน ผิด ("+ str(code) +") ต้องเป็นตัวพิมพ์ใหญ่เท่านั้น ไม่สามารถบันทึกได้ กรุณาใส่รหัสสินค้าใหม่")
        
        cleaned_data['code'] = code
        cleaned_data['name'] = name
        return cleaned_data