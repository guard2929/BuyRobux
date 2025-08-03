from django.urls import path
from . import views

app_name = 'core'
urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('buy_robux_step2/', views.buy_robux_step2, name='buy_step2'),
    path('buy_robux_step3/', views.buy_robux_step3, name='buy_step3'),
    path('buy_confirm', views.buy_confirm, name='buy_confirm'),
    path('social_link/<str:social>/', views.social_link, name='social_link'),
    path('activate_promo/', views.activate_promo, name='activate_promo'),
    path('withdraw_bonus/', views.withdraw_bonus, name='withdraw'),
    path('withdraw_step2/', views.withdraw_step2, name='withdraw_step2'),
    path('withdraw_step3/', views.withdraw_step3, name='withdraw_step3'),
    path('withdraw_confirm/', views.withdraw_confirm, name='withdraw_confirm'),
    path('buy/confirm/<int:purchase_id>/', views.confirm_purchase, name='confirm_purchase'),
    path('activate_promo/', views.activate_promo, name='activate_promo'),
]
