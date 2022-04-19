APPNAME="swiss-rest" #your app name here
curl https://cli-assets.heroku.com/install-ubuntu.sh | sh
heroku login
heroku create $APPNAME
heroku addons:create memcachedcloud