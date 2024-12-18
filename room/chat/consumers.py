
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from .models import Room, UserPoints
from channels.db import database_sync_to_async
room_data = {}

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.user = self.scope['user']
        self.room_group_name = f'chat_{self.room_name}'

        if self.room_name not in room_data:
            room_data[self.room_name] = {
                'competition_ended': False,
                'awarded_users': [],
                'challenge_started': False, 
                'challenge_stopped': False   
            }

       
        if room_data[self.room_name]['competition_ended']:
            await self.send(text_data=json.dumps({
                'competition_ended': True,
                'message': 'Competition has ended. No more rewards available.'
            }))

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

       
        await self.channel_layer.group_send(self.room_group_name, {
            'type': 'user_joined',
            'email': self.user.username
        })

        
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

        # Notify the user leaving
        await self.channel_layer.group_send(self.room_group_name, {
            'type': 'user_left',
            'email': self.user.username,
        })

    async def receive(self, text_data):
        data = json.loads(text_data)

        # Fetch the challenge status from the room
        room = await self.get_room_data(self.room_name)
        
        # If the challenge is paused, prevent sending messages
        if room['challenge_stopped']:
            await self.send(text_data=json.dumps({
                'message': "The challenge is paused. You cannot send messages.",
                'email': self.user.username,
                'points_awarded': 0,
            }))
            return
        
       
        if not room['challenge_started']:
            await self.send(text_data=json.dumps({
                'message': "The challenge has not started yet. You cannot send messages.",
                'email': self.user.username,
                'points_awarded': 0,
            }))
            return

        # Process the message
        if 'message' in data:
            message = data['message']
            email = self.user.username

            target_word = await self.get_target_word(self.room_name)

            if len(room_data[self.room_name]['awarded_users']) >= 3:
              
                await self.send(text_data=json.dumps({
                    'message': "Competition has ended. No more rewards available.",
                    'email': email,
                    'points_awarded': 0, 
                }))
                return

            if target_word and target_word.lower() in message.lower():  
                
                if self.user.username in room_data[self.room_name]['awarded_users']:
                    await self.send(text_data=json.dumps({
                        'message': f"You've already earned points for the target word: {target_word}",
                        'email': email,
                        'points_awarded': 0, 
                    }))
                else:
                    position = len(room_data[self.room_name]['awarded_users'])
                    if position == 0:
                        points = 50  
                    elif position == 1:
                        points = 30  
                    else:
                        points = 10  

                    await self.award_points(self.user, self.room_name, points)
                    room_data[self.room_name]['awarded_users'].append(self.user.username)

                    await self.send(text_data=json.dumps({
                        'message': f"You earned {points} points!", 
                        'email': email,
                        'points_awarded': points,
                    }))

                    await self.channel_layer.group_send(self.room_group_name, {
                        'type': 'chat_message',
                        'message': f"{email} earned {points} points!",  
                        'email': email,
                        'points_awarded': points,
                    })

                   
                    if len(room_data[self.room_name]['awarded_users']) == 3:
                        room_data[self.room_name]['competition_ended'] = True
                        await self.channel_layer.group_send(self.room_group_name, {
                            'type': 'competition_ended',
                            'message': "Competition has ended. No more rewards available.",
                        })

            else:
                await self.channel_layer.group_send(self.room_group_name, {
                    'type': 'chat_message',
                    'message': message,
                    'email': email,
                    'points_awarded': 0, 
                })

        elif 'typing' in data:
            # Send typing indicator
            await self.channel_layer.group_send(self.room_group_name, {
                'type': 'typing_indicator',
                'email': self.user.username
            })

  
    async def user_joined(self, event):
        email = event['email']
        await self.send(text_data=json.dumps({
            'user_joined': f"{email} has joined the room.",
            'email': email,
        }))

    
    async def user_left(self, event):
        email = event['email']
        await self.send(text_data=json.dumps({
            'user_left': f'{email} has left the room.',
            'email': email
        }))

    
    async def chat_message(self, event):
        message = event['message']
        email = event['email']
        points_awarded = event.get('points_awarded', 0)

       
        await self.send(text_data=json.dumps({
            'message': message,
            'email': email,
            'points_awarded': points_awarded,
        }))

 
    async def competition_ended(self, event):
        message = event['message']
        await self.send(text_data=json.dumps({
            'message': message,
        }))

   
    async def typing_indicator(self, event):
        email = event['email']
        await self.send(text_data=json.dumps({
            'typing': f'{email} is typing...',
            'email': email
        }))

    
    @database_sync_to_async
    def get_target_word(self, room_name):
        try:
            room = Room.objects.get(room_name=room_name)
            return room.target_word
        except Room.DoesNotExist:
            return None

    @database_sync_to_async
    def get_room_data(self, room_name):
        try:
            room = Room.objects.get(room_name=room_name)
            return {'challenge_started': room.challenge_started, 'challenge_stopped': room.challenge_stopped}
        except Room.DoesNotExist:
            return {'challenge_started': False, 'challenge_stopped': False}

    @database_sync_to_async
    def award_points(self, user, room_name, points):
        try:
            room = Room.objects.get(room_name=room_name)
            user_points, created = UserPoints.objects.get_or_create(user=user, room=room)
            user_points.points += points
            user_points.save()
        except Room.DoesNotExist:
            pass
