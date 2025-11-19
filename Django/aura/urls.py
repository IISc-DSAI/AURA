"""
URL configuration for aura project.

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
from . import views

# urlpatterns = [
#     path('admin/', admin.site.urls),
    
urlpatterns = [
    # ----- AUTH -----
    path("auth/signup", views.signup, name="signup"),
    path("auth/login", views.login, name="login"),
    path("auth/me", views.me, name="me"),

    # ----- CHATS -----
    path("chats", views.chats, name="chats"),                     # GET=list, POST=create
    path("chats/<int:chat_id>", views.chat_detail, name="chat_detail"),   # PATCH=rename, DELETE=delete
    path("chats/<int:chat_id>/messages", views.chat_messages, name="chat_messages"),

    # ----- MAIN CHAT PIPELINE -----
    path("chat", views.chat, name="chat"),                       # POST → LangGraph pipeline
]

