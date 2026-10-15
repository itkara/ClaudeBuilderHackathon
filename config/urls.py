from django.urls import path
from matching import views
urlpatterns=[path('',views.index),path('api/status',views.status),path('api/profile',views.profile),path('api/upload-cv',views.upload_cv),path('api/match',views.match),path('api/jd',views.jd),path('api/generate',views.generate),path('api/export-pdf',views.export_pdf)]
