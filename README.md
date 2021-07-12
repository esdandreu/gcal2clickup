# gcal2clickup
Google Calendar and Click Up integration. Sycnhronize tasks from calendar events, adding meeting notes.

## Use remote database
Save the `DATABASE_URL` environmental variable with the output of the following
command
```
heroku config:get DATABASE_URL -a <app name>
```

Being `app name` in this case `gcal2clickup`.