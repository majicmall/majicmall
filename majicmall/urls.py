"""
URL configuration for majicmall project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/

Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path
from core.views import (
    homepage,
    mall_home,
    launch_splash,
    merchant_onboard,
    merchant_thank_you,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', homepage, name='home'),
    path('mall/', mall_home, name='mall-home'),
    path('launch/', launch_splash, name='launch-splash'),
    path('merchant/onboard/', merchant_onboard, name='merchant-onboard'),
    path('thank-you/', merchant_thank_you, name='thank-you'),
]
