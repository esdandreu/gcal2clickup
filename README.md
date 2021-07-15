# gcal2clickup
Google Calendar and Click Up integration. Synchronize tasks from calendar
events, adding meeting notes.


# Required environmental variables
Build a `.env` file for local development and add the environmental variables
to your heroku app as config vars.

https://devcenter.heroku.com/articles/config-vars

## Use remote database
Save the `DATABASE_URL` environmental variable with the output of the following
command
```
heroku config:get DATABASE_URL -a <app name>
```

Being `app name` in this case `gcal2clickup`.

## Get google credentials
https://developers.google.com/identity/protocols/oauth2/web-server#python

```
export G_CLIENT_ID="1040180456622-oite6hp72i0a3c4lr70jaee4ot66kvf7.apps.googleusercontent.com"
export G_CLIENT_SECRET="aCNKVwSuaNmYMV7TttAdf0Sg"
```

### Register your domain in google search console
It is required to [set a webhook with Google Calendar
API](https://developers.google.com/calendar/api/guides/push). Follow the
[instructions provided by
Google](https://developers.google.com/calendar/api/guides/push#registering-your-domain),
in the first step, download and save the `html` file as
`google_verification.html` in the root of this project.

# Testing
you can create a new database on heroku and use it for testing
purposes
https://medium.com/analytics-vidhya/provisioning-a-test-postgresql-database-on-heroku-for-your-django-app-febb2b5d3b29
Add the test database uri to the environmental variable `TEST_DATABASE_URL`.

Run tests with 
```
python manage.py test --keepdb
```
Your tests will have to manage the clean-up of the database, not only the setup.