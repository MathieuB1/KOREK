from rest_framework import serializers
from korek.models import Product, ProductImage, ProductVideo, ProductAudio, Profile, GroupAcknowlegment, PasswordReset, ProfileImage
from django.contrib.auth.models import User, Group

import magic
import re

from base64 import b64encode
from os import urandom

from django.conf import settings

from django.core.mail import send_mail

# Notification
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


def guess_type(file_object):
    return magic.from_buffer(file_object.read()[:1024], mime=True).split('/')[0]


 # Ignore some validated Fields
class validated_entries(object):
    val = ""
    def __init__(self, initial_data, list_to_ignore):
        for key in initial_data:
            if key not in list_to_ignore:
                self.val += key + "=validated_data.get('" + key + "'),"
    def get_string(self):
            return self.val

############# KOREK SERIALISERS ##############
class PasswordSerializer(serializers.ModelSerializer):
    class Meta:
        model = PasswordReset
        fields = ('user_email','password',)
        write_only_fields = ('password',)

    def validate_user_email(self, value):
        if User.objects.filter(email=value).count() == 0:
            raise serializers.ValidationError("Enter a valid email address.")
        return value

    def to_representation(self, obj):
        ret = super(PasswordSerializer, self).to_representation(obj)
        ret.pop('password')
        return ret

    def create(self, validated_data):

            PasswordReset.objects.filter(user_email=validated_data['user_email']).delete()

            tmp_url = str(self.context.get('view').request.META['HTTP_HOST'])  + '/reset_password/'+ str(b64encode(urandom(1024)).decode('utf-8')) + '&mail=' + str(validated_data['user_email'])
            password_reset = PasswordReset.objects.create(
                user_email = validated_data['user_email'],
                tmp_url = tmp_url,
                password = validated_data['password'])

            # Email is not mandatory
            if settings.EMAIL_HOST_USER[0] != 'xxxx.yyy@gmail.com':
                send_mail(
                    'Reset Password',
                    '',
                    settings.EMAIL_HOST_USER[0],
                    [validated_data['user_email']],
                    html_message = '<p>Click on this link to reset your password:</p><a href="' + tmp_url + '">Reset Password</a>',
                    fail_silently=False,
                )

            password_reset.save()
            return password_reset


class GroupSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Group
        fields = ('name',)
        extra_kwargs = {
            'name': {'validators': []},
        }






class RequiredFieldsMixin():
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        fields_notrequired = getattr(self.Meta, 'fields_notrequired', None)

        if fields_notrequired:
            for key in self.fields:
                if key in fields_notrequired:
                    self.fields[key].required = False

class UserSerializerRegister(RequiredFieldsMixin, serializers.ModelSerializer):
    groups = GroupSerializer(many=True, required=False, read_only=True)
    my_group = serializers.SerializerMethodField(read_only=True)

    def to_representation(self, obj):
        ret = super(UserSerializerRegister, self).to_representation(obj)
        ret.pop('password')
        return ret
        

    def get_my_group (self, obj):
        if obj.username is not None:
            user = User.objects.get(username=obj.username)
            return Profile.objects.get(user=user).user_group

    class Meta:
        model = User
        fields = ('id', 'username', 'password', 'email', 'first_name', 'last_name','my_group','groups',)
        fields_notrequired = ('password',)
        read_only_fields = ('id',)

    # Need to remove groups
    def validate_email(self, value):
        if value is None or value == '':
            raise serializers.ValidationError("Enter a valid email address.")

        try:
            user = User.objects.get(email=value)
            if self.instance and self.instance.id == user.id:
                return value
        except User.DoesNotExist:
            return value
        
        raise serializers.ValidationError("Email already exists.")

    def validate_password(self, value):
        if value is None or value == '':
            raise serializers.ValidationError("Enter a valid password.")
        if len(value) < 4:
            raise serializers.ValidationError("Password too short.")

        return value

    def update(self, instance, validated_data):
        instance.username = validated_data.get('username', instance.username)
        instance.email = validated_data.get('email', instance.email)
        instance.first_name = validated_data.get('first_name', instance.first_name)
        instance.last_name = validated_data.get('last_name', instance.last_name)


        if validated_data.get('password') is not None:
            instance.set_password(validated_data['password'])

        # Update my Image
        images_data = {}
        for filename, file in  self.context.get('view').request.FILES.items():
            file_object = self.context.get('view').request.FILES[filename]
            profile = Profile.objects.get(user=self.context['request'].user)

            ProfileImage.objects.get(profile=profile).delete(False)
            ProfileImage.objects.create(profile=profile, image=file_object)
            break

        instance.save()
        return instance

    def create(self, validated_data):

        if validated_data.get('email') is None:
            raise serializers.ValidationError("Enter a valid email address.")
        if validated_data.get('password') is None:
            raise serializers.ValidationError("Enter a valid password.")

        user = User.objects.create(
            username=validated_data['username'],
            email=validated_data['email'],
            first_name=validated_data.get('first_name',''),
            last_name=validated_data.get('last_name','')
        )

        user.set_password(validated_data['password'])

        # Create a group for user
        new_group = Group.objects.create(name=b64encode(urandom(256)).decode('utf-8')[10:90])
        new_group.user_set.add(user)
        profile = Profile.objects.create(user=user, user_group=new_group)

        # Save my Image
        images_data = {}
        ProfileImage.objects.create(profile=profile)
        for filename, file in  self.context.get('view').request.FILES.items():
            file_object = self.context.get('view').request.FILES[filename]
            ProfileImage.objects.filter(profile=profile).update(image=file_object)
            break

        user.save()
        return user


class ProductImageSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(required=False, max_length=None, use_url=True,  style={'autofocus': True, 'placeholder': ''})

    class Meta:
        model = ProductImage
        fields = ('image',)


class ProductVideoSerializer(serializers.ModelSerializer):
    video = serializers.FileField(required=False, max_length=None, use_url=True,  style={'placeholder': ''})

    class Meta:
        model = ProductVideo
        fields = ('video',)

class ProductAudioSerializer(serializers.ModelSerializer):
    audio = serializers.FileField(required=False, max_length=None, use_url=True,  style={'placeholder': ''})

    class Meta:
        model = ProductAudio
        fields = ('audio',)

class ProductSerializer(serializers.HyperlinkedModelSerializer):
    owner = serializers.ReadOnlyField(source='owner.username')
    images = ProductImageSerializer(source='productimage_set', required=False, many=True)
    videos = ProductVideoSerializer(source='productvideo_set', required=False, many=True)
    audios = ProductAudioSerializer(source='productaudio_set', required=False, many=True)
    barcode =  serializers.IntegerField(required=False, style={'hide_label': False, 'placeholder': '0'})

    highlight = serializers.HyperlinkedIdentityField(view_name='product-highlight', format='html', read_only=True)

    class Meta:
        model = Product
        fields = ('url', 'id', 'created', 'highlight', 'title', 'subtitle', 'text', 'barcode', 'brand', 'owner', 'language','images','videos','audios','lat','lon')

    # Image & Videos are not taken into account for updating Product
    # A lot of logic here if we want support media files
    def update(self, instance, validated_data):
        instance.title = validated_data.get('title', instance.title)
        instance.subtitle = validated_data.get('subtitle', instance.subtitle)
        instance.text = validated_data.get('text', instance.text)
        instance.barcode = validated_data.get('barcode', instance.barcode)
        instance.brand = validated_data.get('brand', instance.brand)
        instance.language = validated_data.get('language', instance.language)
        instance.lat = validated_data.get('lat', instance.lat)
        instance.lon = validated_data.get('lon', instance.lon)

        instance.save()

        tmp_highlight = u''
        for key, value in instance.__dict__.items():
             if not key.startswith('_') and key != ('highlight'):
                 tmp_highlight +=  u'<p>%s:%s</p>' % (key, value)

        product_highlight = Product.objects.get(id=instance.id).highlight
        regex = re.compile(r'(<div id="text">)(.*?)(</div><div id="separator"></div>)')
        replaced = regex.sub(r"\1" + tmp_highlight + r"\3", product_highlight, 1)

        Product.objects.filter(id=instance.id).update(highlight=replaced)
        
        return instance

        
    def create(self, validated_data):

        EXT_IMAGE_LIST = ['gif','png','jpg','bmp','jpe','jpeg','tif','tiff']
        EXT_VIDEO_LIST = ['mkv','avi','mp4','flv','mpeg','wmv','mov']
        EXT_AUDIO_LIST = ['mp3','ogg']

        images_data = {}
        videos_data = {}
        audios_data = {}
        tmp_highlight = ''

        for filename, file in  self.context.get('view').request.FILES.items():
            file_object = self.context.get('view').request.FILES[filename]
            ext = file_object.name.split('.')[-1].lower()

            if ext in EXT_IMAGE_LIST:
                try:
                    file_type = guess_type(file_object)
                    if file_type == 'image':
                        images_data[file_object.name] = file_object
                except:
                    pass

            elif ext in EXT_VIDEO_LIST:
                try:
                    file_type = guess_type(file_object)
                    if file_type == 'video':
                        videos_data[file_object.name] = file_object
                except:
                    pass

            elif ext in EXT_AUDIO_LIST:
                try:
                    file_type = guess_type(file_object)
                    if file_type == 'audio':
                        audios_data[file_object.name] = file_object
                except:
                    pass

        validated_fields_ignored = validated_entries(validated_data,['productimage_set','productvideo_set', 'productaudio_set'])
        product = eval("Product.objects.create(" + validated_fields_ignored.get_string()[:-1] + ")")

        tmp_highlight += u'<!DOCTYPE html>' \
                         u'<body><div id="text">'
        for key, value in product.__dict__.items():
             if not key.startswith('_') and key != ('highlight'):
                 tmp_highlight +=  u'<p>%s:%s</p>' % (key, value)
        tmp_highlight += u'</div>' \
                         u'<div id="separator"></div>'

        if images_data is not None or videos_data is not None:

            tmp_highlight += u'<div id="media"><div id="images">'     
            for image_data in images_data.values():
                stored_image = ProductImage.objects.create(product=product, image=image_data)
                tmp_highlight += u'<img src="%s"/>' % stored_image.image.url
            tmp_highlight += u'</div>'

            tmp_highlight += u'<div id="videos">'         
            for video_data in videos_data.values():
                stored_video = ProductVideo.objects.create(product=product, video=video_data)
                tmp_highlight += u'<video controls><source src="%s"></video>' % stored_video.video.url
            tmp_highlight += u'</div>'

            tmp_highlight += u'<div id="audios">'         
            for audio_data in audios_data.values():
                stored_audio = ProductAudio.objects.create(product=product, audio=audio_data)
                tmp_highlight += u'<audio controls><source src="%s"></audio>' % stored_audio.audio.url
            tmp_highlight += u'</div></div></body></html>'

        # Can be desactivated if not needed
        Product.objects.filter(id=product.id).update(highlight=tmp_highlight)

        return product


class GroupSerializerOwner(serializers.ModelSerializer):
    groups = GroupSerializer(many=True)
    
    class Meta:
        model = User
        fields = ('id','username','groups',)
        read_only_fields = ('id','username',)

    def validate_groups(self, value):
        for el in value:
            try:
                user_to_add = User.objects.get(username=el['name'])
                Profile.objects.get(user=user_to_add.id).user_group
            except:
                raise serializers.ValidationError("%s in not a valid username." % el['name'])

        return value

    def update(self, instance, validated_data):
        user = User.objects.get(username=instance.username)

        for group in validated_data['groups']:

            group_to_add = group['name']
            user_to_add = User.objects.get(username=group['name'])
            group_to_add = Profile.objects.get(user=user_to_add.id).user_group


            # Check if user already in group
            if not user.groups.filter(name=group_to_add).exists():

                # Add user to group
                request_group = Group.objects.get(name=group_to_add)
                if settings.PRIVACY_MODE[0] == 'PRIVATE':
                    request_group.user_set.add(user)

                user_profile = Profile.objects.get(user_group=request_group.name)
                owner = User.objects.get(username=user_profile.user)

                user_group = Profile.objects.get(user=user)

                # Share asker group
                if settings.PRIVACY_MODE[0] == 'PRIVATE':
                    existing_group = Group.objects.get(name=user_group.user_group)
                    existing_group.user_set.add(owner)

                    # Notification
                    try:
                        channel_layer = get_channel_layer()

                        event = 'event_%s' % (user)
                        async_to_sync(channel_layer.group_send)(event, {"type": "event_message", "message": user.username + " has been added!"})
                        event = 'event_%s' % (user_to_add)
                        async_to_sync(channel_layer.group_send)(event, {"type": "event_message", "message": user_to_add.username + " has been added!"})
                    except:
                        pass
                else:
                    # PRIVATE-VALIDATION
                    pending_group = GroupAcknowlegment.objects.get_or_create(group_asker=user, group_asker_username=user.username, group_name=request_group.name, group_owner=owner, activate=False)

                    # Notification
                    try:
                        channel_layer = get_channel_layer()
            
                        event = 'event_%s' % (user)
                        async_to_sync(channel_layer.group_send)(event, {"type": "event_message", "message": user_to_add.username + " request received!"})
                        event = 'event_%s' % (user_to_add)
                        async_to_sync(channel_layer.group_send)(event, {"type": "event_message", "message": user.username + " request pending!"})
                    except:
                        pass

            # Friend has been already added
            else:
                # Notification
                try:
                    channel_layer = get_channel_layer()
                    event = 'event_%s' % (user)
                    async_to_sync(channel_layer.group_send)(event, {"type": "event_message", "message": user_to_add.username + " already added!"})
                except:
                    pass

        if settings.PRIVACY_MODE[0] == 'PRIVATE':
            return user
        else:
            return validated_data



class GroupAcknowlegmentSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = GroupAcknowlegment
        fields = ('id', 'group_asker','group_asker_username','group_name','group_owner','activate',)
        read_only_fields = ('id','group_owner','group_asker','group_name','group_asker_username')

    def update(self, instance, validated_data):

        group_asker = validated_data.get('group_asker', instance.group_asker)
        group_name = validated_data.get('group_name', instance.group_name)
        group_owner = validated_data.get('group_owner', instance.group_owner)

        user_asker = User.objects.get(username=group_asker)

        if validated_data['activate']:

            existing_group = Group.objects.get(name=group_name)
            existing_group.user_set.add(user_asker)

            # Share asker group
            user = User.objects.get(username=group_owner)

            asker = User.objects.get(username=group_asker)
            user_group = Profile.objects.get(user=asker)

            existing_group = Group.objects.get(name=user_group.user_group)
            existing_group.user_set.add(user)

            # Notification
            try:
                channel_layer = get_channel_layer()
                event = 'event_%s' % (user_asker)
                async_to_sync(channel_layer.group_send)(event, {"type": "event_message", "message": user.username + " accepted the request!"})

                event = 'event_%s' % (user)
                async_to_sync(channel_layer.group_send)(event, {"type": "event_message", "message": user_asker.username + " request validated!"})
            except:
                pass

        GroupAcknowlegment.objects.get(group_asker=group_asker, group_name=group_name).delete()

        # Notification
        if not validated_data['activate']:
            try:
                channel_layer = get_channel_layer()
                event = 'event_%s' % (user_asker)
                async_to_sync(channel_layer.group_send)(event, {"type": "event_message", "message": user.username + " rejected " + user_asker.username + " request!"})
            except:
                pass

        instance.activate = validated_data['activate']
        return instance



class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username',)

class ProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    class Meta:
        model = Profile
        fields = ('user',)

class ProfileImageSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    profile = ProfileSerializer()
    class Meta:
        model = ProfileImage
        fields = ('id','image','profile',)
        read_only_fields = ('profile',)
        




