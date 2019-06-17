from flask import Flask, json
from flask_sqlalchemy import SQLAlchemy
from flask_ckeditor import CKEditor
import boto3
import os

app = Flask(__name__)

app.config['SECRET_KEY'] = 'f03b64dca19c7e6e86b419e8c3abf4db'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///batches.db'


# app.config['CKEDITOR_SERVE_LOCAL'] = True
# app.config['CKEDITOR_EXTRA_PLUGINS'] = ['codemirror']
app.config['CKEDITOR_HEIGHT'] = 600


app.config.from_pyfile('cred.cfg')

db = SQLAlchemy(app)
ckeditor = CKEditor(app)

ISO3166 = ""
filename = os.path.join(app.instance_path, 'iso3166cc.json')
with open(filename) as f:
    ISO3166 = json.load(f)


# Connect to MTurk-Server

endpoint_url = 'https://mturk-requester-sandbox.us-east-1.amazonaws.com'

# Uncomment this line to use in production
# endpoint_url = 'https://mturk-requester.us-east-1.amazonaws.com'
# connect to mturk client using AWS credentials

# If results of >100 entries are necessary it might be necessary to use boto3-paginators
client = boto3.client('mturk', endpoint_url=endpoint_url, region_name='us-east-1',
                      aws_access_key_id=app.config['AWS_ACCESS_KEY_ID'],
                      aws_secret_access_key=app.config['AWS_SECRET_ACCESS_KEY'])

if client:
    print(" *** Connected to MTurk-Server *** ")

from flask_mturk import routes
