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
        company_tab = BaseBranchCompany.objects.filter(userprofile = user_profile)
        company_code = BaseBranchCompany.objects.filter(userprofile = user_profile).values('code')
    except:
        company_tab = None

    return dict(company_tab = company_tab)