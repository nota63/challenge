from django.shortcuts import render, redirect, get_object_or_404
from .forms import RoomForm
from .models import Room, Invitation
from django.views import View
from django.http import JsonResponse
from plyer import notification
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.views import View
from django.http import JsonResponse
from .models import Room, UserPoints
from .forms import RoomForm
from django.contrib import messages
from django.urls import reverse
from plyer import notification  
from django.core.mail import send_mail
from django.template.loader import render_to_string
import json
from django.http import HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt

# Create your views here.

image_path = 'chat/cal.ico'

# ACCEPT OR REJECT INVITATIONS

@login_required
def invitation_list(request):
    """Display all invitations to the logged in user"""
    invitations = Invitation.objects.filter(user=request.user,accepted=False)
    return render(request,'chat/invitation_list.html',{'invitations':invitations})

@login_required
def accept_invitation(request, invitation_id):
    """Accept the invitation to a room."""
 
    invitation = get_object_or_404(Invitation, id=invitation_id, user=request.user)


    invitation.accept_invitation()  

    messages.success(request, 'You have successfully joined the room.')
    return redirect('join_chat', room_name=invitation.room.room_name)  


@login_required
def reject_invitation(request, invitation_id):
    """Reject the invitation."""
    
    invitation = get_object_or_404(Invitation, id=invitation_id, user=request.user)

    
    invitation.reject_invitation()  
    messages.success(request,'Invitation has been rejected successfully')

    messages.info(request, 'Invitation has been rejected.')
    return redirect('invitation_list')  


    






class SelectorView(View):
    template_name = 'chat/selector.html'

    def get(self, request):
        return render(request, self.template_name)
    





image_path = 'chat/cal.ico'



class JoinRoomView(View):
    template_name = 'chat/create_room.html'

    def get(self, request):
        form = RoomForm(request=request)  
        room = None

        if 'room_name' in request.GET:  
            room_name = request.GET.get('room_name')
            try:
                room = Room.objects.get(room_name=room_name)
            except Room.DoesNotExist:
                room = None

        
        return render(request, self.template_name, {'form': form, 'room': room})

    def post(self, request):
        form = RoomForm(request.POST, request=request)  
        if form.is_valid():
            try:
                room = form.save()  

              
                room.users.add(request.user)

              
                notification.notify(
                    title='Calendar +',
                    message='Room Created Successfully!',
                    app_icon=image_path if image_path else None,
                    timeout=5
                )

               
                return redirect(reverse('join_chat', kwargs={'room_name': room.room_name}))
            except Exception as e:
                return JsonResponse({'error': str(e)}, status=500)

        return render(request, self.template_name, {'form': form}) 


# main
@login_required
def join_chat(request, room_name):
    try:
        room = Room.objects.get(room_name=room_name)
    except Room.DoesNotExist:
        room = None
    
  
    if room:
        room_link = reverse('join_chat', kwargs={'room_name': room_name})
        room_link = request.build_absolute_uri(room_link) 
    else:
        room_link = None

    return render(request, 'chat/join_chat.html', {'room_name': room_name, 'room': room, 'room_link': room_link})







# view to set target view
class SetTargetWordView(View):
    def post(self, request, room_name):
        try:
            room = Room.objects.get(room_name=room_name)

            if room.created_by != request.user:
                return JsonResponse({'error': 'You are not authorized to modify the target word.'}, status=403)

            data = json.loads(request.body)

           
            if 'target_word' in data:
                target_word = data.get('target_word')
                room.target_word = target_word
                room.save()
                return JsonResponse({'success': True, 'message': 'Target word set successfully.'})
            else:
                room.target_word = None
                room.save()
                return JsonResponse({'success': True, 'message': 'Target word removed successfully.'})

        except Room.DoesNotExist:
            return JsonResponse({'error': 'Room not found.'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)




# check targeted word 
class CheckTargetWordView(View):
    def post(self, request, room_name):
        try:
           
            room = Room.objects.get(room_name=room_name)

            target_word = room.target_word

          
            message = request.POST.get('message')

         
            user = request.user

           
            if target_word and target_word.lower() in message.lower():
               
                return JsonResponse({'success': True, 'message': 'Message matched the target word!'}, status=200)
            else:
                return JsonResponse({'success': False, 'message': 'No match to target word.'}, status=200)

        except Room.DoesNotExist:
            return JsonResponse({'error': 'Room not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
        


# get users points
def get_user_points(request, room_name):
    try:
        
        room = Room.objects.get(room_name=room_name)
    except Room.DoesNotExist:
       
        raise HttpResponseForbidden("Room not found.")

   
    user_points = UserPoints.objects.filter(room=room).order_by('-points')

    if not user_points.exists():
        
        return JsonResponse({'points_data': []})

    points_data = [{
        'username': user_points.user.username,
        'points': user_points.points,
    } for user_points in user_points]

    return JsonResponse({'points_data': points_data}) 


# start or stop the challenge
@csrf_exempt
def start_stop_challenge(request, room_id):
    # Ensure that only the room creator can start/stop the challenge
    room = get_object_or_404(Room, id=room_id)

    if request.user != room.created_by:
        return JsonResponse({"error": "You are not the room creator!"}, status=403)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON data"}, status=400)

    action = data.get('action')

    if action == 'start':
        if room.challenge_started:
            return JsonResponse({"error": "The challenge has already started."}, status=400)

        room.challenge_started = True
        room.challenge_stopped = False
        room.save()
        return JsonResponse({"success": "Challenge has started!"})

    elif action == 'pause':
        if not room.challenge_started or room.challenge_stopped:
            return JsonResponse({"error": "The challenge is not active to pause."}, status=400)

        room.challenge_stopped = True
        room.save()
        return JsonResponse({"success": "Challenge has been paused!"})

    elif action == 'resume':
        if not room.challenge_started or not room.challenge_stopped:
            return JsonResponse({"error": "The challenge is not paused to resume."}, status=400)

        room.challenge_stopped = False
        room.save()
        return JsonResponse({"success": "Challenge has resumed!"})

    elif action == 'stop':
        if not room.challenge_started:
            return JsonResponse({"error": "The challenge has not started yet."}, status=400)

        room.challenge_started = False
        room.challenge_stopped = False
        room.save()
        return JsonResponse({"success": "Challenge has been stopped!"})

    return JsonResponse({"error": "Invalid action!"}, status=400)


