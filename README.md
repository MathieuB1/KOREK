# Nginx + Swagger +  Django REST + PostGreSQL + Collectd + InfluxDB + Grafana

Another DRF Swagger starter kit based on docker-compose and django REST server including features:

 - User and Group management for POST requests (Auth protocol + JWT)
 - Support Images & Videos & Audios
 - Media protection
 - Password Reset (with smtp replacement see docker-compose)
 - DashBoard Monitoring
 - Notification for friend request provided by ASGI

#### Demo of the Rest API on GCP

http://104.155.1.18

> user: toto password: toto
> user: toto1 password: toto

#### An API documentation generator for Swagger UI, Django REST Framework & PostGreSQL

## Requirements
docker-compose installation https://docs.docker.com/compose/install/

## Installation

1. ```git clone https://github.com/MathieuB1/KOREK --config core.autocrlf=input```

2. Configuration (Optional)

* Configure the server storage in the docker-compose.yml option PRIVACY_MODE=PUBLIC/PRIVATE/PRIVATE-VALIDATION

> PUBLIC: Everyone can access to other posts<br/>
> PRIVATE: User can access to other posts only if they share their group id<br/>
> PRIVATE-VALIDATION: User can access to other posts only if the Owner accepts the invitation<br/>

* Configure DEBUG mode in the docker-compose.yml option DEBUG=True/False
* Configure mail for password reset option EMAIL_HOST_USER, EMAIL_HOST_PASSWORD, EMAIL_HOST

3. ```docker-compose down && docker volume prune -f && docker-compose build && docker-compose up```

4. Open your navigator and go to localhost

## Usage

1. Create a user with the swagger localhost/register api
2. You must login to access to POST, PUT and DELETE methods defined in the Korek api.

![alt text](https://github.com/MathieuB1/KOREK/blob/master/doc/img/swagger.jpg)

## Testing KOREK API
```
docker exec -it $(docker ps | grep web_rest_1 | awk '{print $NF}') /bin/bash -c "cd /code && python runtests.py"
```

> test_end_to_end_korek.py

* Create Users
* Get CSRF token
* Reset Password (need a valid mail server see "Configure mail for password")
* Create Products for Users
* Get JWT Bearer token and create a Product
* Validate Groups view permission when Users are friends
* Validate security access when targetting media urlencoded
* Check Product accessibilty for all Users
* Validate full Product deletion
* Check cascading deletion when deleting Users

## Curl POST one Product

curl -X POST \
  http://localhost/products/ \
  -H 'Accept: application/json' \
  -H 'Authorization: Basic YW15OmFteQ==' \
  -H 'Cache-Control: no-cache' \
  -H 'X-CSRFToken: zOLHPXFOun7t17vH4vTypgMcQPCFolVa4dzfagAKT6zQmCM3s16e7lHZtM48Pcld' \
  -F title=rg \
  -F brand=gt \
  -F text=toto \
  -F barcode=23 \
  -F language=fr \
  -F 'image1=@C:\Users\Mathieu\Pictures\index1.jpeg' \
  -F 'image2=@C:\Users\Mathieu\Pictures\Screenshots\index2.png' \
  -F 'image3=@C:\Users\Mathieu\Pictures\index3.jpg' \
  -F 'image4=@C:\Users\Mathieu\Pictures\index1.jpg'

# Grafana
admin/admin
localhost:3000

![alt text](https://github.com/MathieuB1/KOREK/blob/master/doc/img/dashboard.jpg)

# Django login
Use `korek` as admin user and password for login

# PostGreSQL
postgresql/postgresql
localhost:5050

# InfluxDB
root/root
localhost:8083