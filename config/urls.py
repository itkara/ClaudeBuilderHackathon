from django.contrib.auth import views as auth_views
from django.urls import path
from matching import views
from matching.registration import register
from django.views.generic import RedirectView
from django.contrib import admin
from matching.login import HireationshipLoginView
urlpatterns=[path('admin/', admin.site.urls),path('judges/', RedirectView.as_view(url='/register/', query_string=True, permanent=False), name='judges'),path('register/',register,name='register'),path('login/', HireationshipLoginView.as_view(), name='login'),path('logout/', auth_views.LogoutView.as_view(next_page='/login/'), name='logout'),path('',views.index),path('api/generation-quota',views.generation_quota),path('api/workspace',views.workspace),path('api/status',views.status),path('api/live-jobs',views.live_jobs),path('api/profile',views.profile),path('api/upload-cv',views.upload_cv),path('api/match',views.match),path('api/jd',views.jd),path('api/generate',views.generate),path('api/export-pdf',views.export_pdf)]
