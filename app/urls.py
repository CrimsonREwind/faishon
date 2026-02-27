from django.urls import path
from . import views
from . import api_views

urlpatterns = [
    path('', views.home, name='home'),
    path('settings/', views.settings_view, name='settings'),
    
    # Address Management
    path('settings/address/add/', views.add_address, name='add_address'),
    path('settings/address/<int:address_id>/edit/', views.edit_address, name='edit_address'),
    path('settings/address/<int:address_id>/delete/', views.delete_address, name='delete_address'),
    path('settings/address/<int:address_id>/set_default/', views.set_default_address, name='set_default_address'),
    
    path('landing/', views.landing, name='landing'),
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    
    # API endpoints
    path('api/generate/', api_views.generate_ideas, name='generate_ideas'),
    path('api/instructions/', api_views.generate_instructions, name='generate_instructions'),
]
