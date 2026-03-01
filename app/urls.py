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

    # Community Feed
    path('community/', views.community_view, name='community'),
    path('community/post/new/', views.create_post, name='create_post'),
    path('community/post/<int:post_id>/like/', views.like_post, name='like_post'),
    path('community/post/<int:post_id>/comment/', views.add_comment, name='add_comment'),
    path('community/post/<int:post_id>/delete/', views.delete_post, name='delete_post'),
    path('community/post/<int:post_id>/edit/', views.edit_post, name='edit_post'),
    path('community/comment/<int:comment_id>/delete/', views.delete_comment, name='delete_comment'),

    path('landing/', views.landing, name='landing'),
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),

    # Donation
    path('donation/', views.donation_view, name='donation'),
    path('donation/new/', views.create_donation, name='create_donation'),
    path('donation/<int:donation_id>/cancel/', views.cancel_donation, name='cancel_donation'),

    # API endpoints
    path('api/generate/', api_views.generate_ideas, name='generate_ideas'),
    path('api/instructions/', api_views.generate_instructions, name='generate_instructions'),
]
