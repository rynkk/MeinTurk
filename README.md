
# CUSTOM MTURK FRAMEWORK: MeinTurk

  

This custom implementation of the MTurk-API introduces a wide array of new functionalities that are not part of the MTurk-Website. The goal is to create a feature rich alternative to the native MTurk solution.

You will need an own server to run this app (even though you can of course just run it locally).
Note thatMeinTurk is WIP, so features might change or be added at any point and there might be instabilities.


 For criticism or suggestions email me: [jannik.meinecke@stud.uni-hannover.de](jannik.meinecke@stud.uni-hannover.de)
  

## Features:
- MiniBatching: Split HITs in Mini-HITs with only one click to save up to 20% of MTurk fees
- Web application: Work on your surveys from anywhere around the globe and have colleagues pitch in for help
- Fullblown alternative: This tool offers almost all of MTurk's functionalities, so that should never need go back
- Softblocking: Tired of getting bad ratings because you block people? MeinTurk introduces a way to tackle this problem by using qualifications to softblock people from participating in your studies.
- Full i18n support: Need to translate this tool to another language? No problem, simply follow the instructions of the translations.txt that is located inside the app
- Configurability: Want to set the highest amount you could possibly pay as a bonus to avoid terrible mistakes? This piece of software offers you a way to enter different parameters inside a configuration file to prevent them.
- Batch archiving: If you are done with a study, but want to keep it locally you can archive a Batch. This will delete the survey from the MTurk-Database but save it on this apps database. Great way to reduce loading times!
- Follow-up surveys: This tool makes it easier for you to make surveys dependant on each other.
- Guaranteed participation: MeinTurk will automatically expand MiniBatched HITs if it doesn't reach the wanted numbers. You can also edit this number on the fly to increase sample sizes of already published HITs!
- Logging: In the case that anything goes wrong you can check the logs that will have every error and other process that ever happend at disposal

## Testing the app locally

If you want to run this app locally simply go into the cloned folder and run these commands (You may want to use a virtual enviroment):
```bash

	>pip install -r requirements.txt

	>python run.py

```
Now you can use the app by accessing 127.0.0.1:5000 on the browser of your choosing.

  
  

## Installation (CentOS)

### Step 0 - Cloning the git repository:
```bash

    >cd <path>
    >git clone https://the-mission.teamusec.de/students/ba-meinecke.git
    
```


### Step 1 - Configuring the settings.cfg:
To make MeinTurk work in conjunction with your MTurk-Account you will need to configure the settings.cfg accordingly. Note that the first 4 lines are mandatory.
```bash

    >cd <path>/ba-meinecke/flask_mturk/settings.cfg   
    
```

Then paste the following (Use a newly created Qualification for the Softblock-ID):
```bash
	AWS_ACCESS_KEY_ID = '<YOUR_ACCESS_KEY>'
    AWS_SECRET_ACCESS_KEY = '<YOUR_SECRET_ACCESS_KEY>'
    SOFTBLOCK_QUALIFICATION_ID = '<YOUR_QUALIFICATION_ID>'
    SANDBOX = False
    DEFAULT_REJECTION_MESSAGE = 'The quality of your answer does not match our quality standards. Thank you for participating.'
    MAX_BONUS = 5.0
    MAX_PAYMENT = 10.0     
```

### Step 2 - Installing dependencies:
```bash

    >sudo python3 -m pip install -r <path>/ba-meinecke/requirements.txt
    
```

### Step 3 - Creating a service to link MeinTurk and uWSGI:
```bash

    >sudo nano /etc/systemd/system/meinturk.service
    
```

Copy and paste the following snippet into the file:

    [Unit]
    Description=uWSGI instance to serve meinturk
    After=network.target

    [Service]
    WorkingDirectory=<path>/ba-meinecke
    ExecStart= /usr/bin/uwsgi --ini <path>/ba-meinecke/app.ini

    [Install]
    WantedBy=multi-user.target

### Step 4 - Linking uWSGI and nginx
```bash

    >sudo nano /etc/nginx/nginx.conf
    
```
Paste this snippet right above the first definiton of the first server:


    auth_basic "Restricted"; # OPTIONAL for password protection of the website
    auth_basic_user_file /etc/nginx/.htpasswd; # OPTIONAL for password protection of the website

    server {
        server_name <YOURSERVER>;
        
        location / {
            include uwsgi_params;
            uwsgi_pass unix:///var/run/meinturk.sock;
        }
    }

Make sure there are no errors in that file by validating it:
```bash

    >sudo /usr/sbin/nginx -t -c /etc/nginx/nginx.conf 
    
```

### Optional: Step 5 - Put a password on your website:
In case you did **not** put both of the optional lines into the file you can skip this step.

You will neeed *htpasswd* for this step, so if you do not have it right now go ahead and install it:
```bash

    >sudo yum install httpd-tools
    
```
Now you can create the *htpasswd*-file:
```bash

    >sudo htpasswd -c /etc/nginx/.htpasswd <USERNAME>
    
```
Use the chosen username and password to log into the website once it is up and running.

### Step 6 - Starting MeinTurk
Use
```bash

    >sudo systemctl start meinturk
    >sudo systemctl enable meinturk
    
```
to start the application and also make it start on every boot up.

Also make sure that nginx is running:
```bash

    >sudo systemctl start nginx
    
```


