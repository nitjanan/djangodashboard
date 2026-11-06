from dbapp.models import UserProfile, BaseVisible, BaseBranchCompany

def userVisibleTab(request):
    try:
        user_profile = UserProfile.objects.get(user_id = request.user.id)
        visible_tab = BaseVisible.objects.filter(userprofile = user_profile)
    except:
        visible_tab = None

    return dict(visible_tab = visible_tab)


def companyVisibleTab(request):
    try:
        user_profile = UserProfile.objects.get(user_id = request.user.id)
        # เรียงตามรหัสบริษัท (00 ทั้งหมด, 01, 02, ...) ให้ลำดับแท็บคงที่
        company_tab = BaseBranchCompany.objects.filter(userprofile = user_profile).order_by('id')
    except:
        company_tab = None

    return dict(company_tab = company_tab)