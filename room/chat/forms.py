from django import forms
from .models import Room, Invitation
from django.contrib.auth.models import User

class RoomForm(forms.ModelForm):
    users_to_invite = forms.ModelMultipleChoiceField(
        queryset=User.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label='Invite Users'
    )

    class Meta:
        model = Room
        fields = ['room_name']

    def __init__(self, *args, **kwargs):
        # Ensure the form gets the request context (e.g., request.user) for setting created_by
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        # Save the Room object first
        room = super().save(commit=False)
        
        # Set the created_by field to request.user
        if self.request and self.request.user:
            room.created_by = self.request.user
        
        # Save the room if commit=True
        if commit:
            room.save()
        
        # After the room is saved, invite the selected users
        users_to_invite = self.cleaned_data.get('users_to_invite', [])
        for user in users_to_invite:
            Invitation.objects.create(room=room, user=user)

        return room
