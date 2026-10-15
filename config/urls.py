from django.contrib.auth import views as auth_views
from django.urls import path
from matching import views
urlpatterns=[path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),path('logout/', auth_views.LogoutView.as_view(next_page='/login/'), name='logout'),path('',views.index),path('api/status',views.status),path('api/live-jobs',views.live_jobs),path('api/profile',views.profile),path('api/upload-cv',views.upload_cv),path('api/match',views.match),path('api/jd',views.jd),path('api/generate',views.generate),path('api/export-pdf',views.export_pdf)]
