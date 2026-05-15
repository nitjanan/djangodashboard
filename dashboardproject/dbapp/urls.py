from django.urls import path
from dbapp import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about),
    path('login/', views.LoginView, name='login'),
    path('logout/', views.LogoutView, name='logout'),
	path('reset_password/', auth_views.PasswordResetView.as_view(template_name = "account/forgotPassword.html"),
          name="reset_password"),

    path('reset_password_send/', auth_views.PasswordResetDoneView.as_view(template_name = "account/resetPasswordSend.html"),
          name="password_reset_done"),
    path('reset/<uidb64>/<token>', auth_views.PasswordResetConfirmView.as_view(template_name = "account/passwordResetConfirm.html"), name="password_reset_confirm"),
    path('reset_password_complete/', auth_views.PasswordResetCompleteView.as_view(template_name = "account/passwordResetComplete.html"), name="password_reset_complete"),

    path('setDateInDashbord', views.setDateInDashbord, name="setDateInDashbord"),
    path('getApiDataToDashbord/', views.getApiDataToDashbord, name="getApiDataToDashbord"),
    path('setSessionCompany/', views.setSessionCompany, name="setSessionCompany"),
    path('updateValueAPI/', views.updateValueAPI, name="updateValueAPI"),
]