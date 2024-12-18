from django.urls import path
from .views import *
from . import views

# app_name ='chat'

urlpatterns=[
    path('create_room/', JoinRoomView.as_view(), name='create_room'),
    path('join_chat/<str:room_name>/', join_chat, name='join_chat'),
    path('selector_room/',SelectorView.as_view(), name='selector_room'),

    # invitation handle
    path('invitations/', views.invitation_list, name='invitation_list'),
    path('invitations/accept/<int:invitation_id>/', views.accept_invitation, name='accept_invitation'),
    path('invitations/reject/<int:invitation_id>/', views.reject_invitation, name='reject_invitation'),


    path('chat/set_target_word/<str:room_name>/', SetTargetWordView.as_view(), name='set_target_word'),


    # check targeted word
    path('check-target-word/<str:room_name>/', CheckTargetWordView.as_view(), name='check_target_word'),

   # get users points
    path('room/<str:room_name>/get_points/', views.get_user_points, name='get_user_points'),

    # start or stop the challenge
    path('room/<int:room_id>/start-stop-challenge/', views.start_stop_challenge, name='start_stop_challenge'),
]
