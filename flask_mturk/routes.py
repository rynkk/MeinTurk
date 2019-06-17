from flask import render_template, url_for, flash, redirect, jsonify, json
from flask_mturk import app, db, client, ISO3166
from flask_mturk.forms import SurveyForm, QualificationsForm, FieldList, FormField, SelectField
from flask_mturk.models import User


balance = None
new_balance = client.get_account_balance()['AvailableBalance']
if new_balance != balance:
    print(" Balance changed")
balance = new_balance

# qualifications = client.list_qualification_types(
# Query="System Qualification",
# MustBeRequestable=False,
# MustBeOwnedByCaller=False,
# MaxResults=10
# )['QualificationTypes']


def get_custom_qualifications():
    return client.list_qualification_types(
        MustBeRequestable=False,
        MustBeOwnedByCaller=True,
    )['QualificationTypes']


system_qualifications = [
    {
        'Type': 'system',
        'Name': 'Worker_NumberHITsApproved',
        'QualificationTypeId': '00000000000000000040',
        'Comparators': [{'value': 'GreaterThan', 'name': 'größer als'}, {'value': 'GreaterThanOrEqualTo', 'name': 'größer als oder gleich'}, {'value': 'LessThan', 'name': 'kleiner als'},
                        {'value': 'LessThanOrEqualTo', 'name': 'kleiner als oder gleich'}, {'value': 'EqualTo', 'name': 'gleich'}, {'value': 'NotEqualTo', 'name': 'nicht gleich'}],
        'Value': 'IntegerValue',  # >=0
        'Default': {"comparator": 'GreaterThan', "val": 100}
    },
    {
        'Type': 'system',
        'Name': 'Worker_Locale',
        'QualificationTypeId': '00000000000000000071',
        'Comparators': [{'value': 'EqualTo', 'name': 'gleich'}, {'value': 'NotEqualTo', 'name': 'nicht gleich'}, {'value': 'In', 'name': 'aus'}, {'value': 'NotIn', 'name': 'nicht aus'}],
        'Value': 'LocaleValue',  # https://docs.aws.amazon.com/de_de/AWSMechTurk/latest/AWSMturkAPI/ApiReference_LocaleDataStructureArticle.html
        'Default': {"comparator": 'EqualTo', 'val': 'US'}
    },
    {
        'Type': 'system',
        'Name': 'Worker_PercentAssignmentsApproved',
        'QualificationTypeId': '000000000000000000L0',
        'Comparators': [{'value': 'GreaterThan', 'name': 'größer als'}, {'value': 'GreaterThanOrEqualTo', 'name': 'größer als oder gleich'}, {'value': 'LessThan', 'name': 'kleiner als'},
                        {'value': 'LessThanOrEqualTo', 'name': 'kleiner als oder gleich'}, {'value': 'EqualTo', 'name': 'gleich'}, {'value': 'NotEqualTo', 'name': 'nicht gleich'}],
        'Value': 'PercentValue',  # 0<=x<=100
        'Default': {"comparator": 'GreaterThanOrEqualTo', 'val': 95}
    }
]
"""  {
        'Name': 'Masters',
        'QualificationTypeId': '2ARFPLSP75KLA8M8DH1HTEQVJT3SY6',  # Sandbox
        # 'QualificationTypeId': '2F1QJWKUDD8XADTFD2Q0G6UTO95ALH',  # Production
        'Comparators': ['Exists']
    },
    {
        'Name': 'Worker_Adult',
        'QualificationTypeId': '00000000000000000060',
        'Comparators': ['EqualTo'],
        'Val': 'IntegerValue'  # 1=true(required), 0=false(not required)
    },
]"""
# print("\n")

# print(system_qualifications)


@app.route("/")
@app.route("/dashboard")
def dashboard():
    response = client.list_hits()
    print(response)
    return render_template('main/dashboard.html', surveys=response, balance=balance)


@app.route("/survey", methods=['GET', 'POST'])
def survey():
    form = SurveyForm()

    percentage_interval = 5
    integer_list = [1, 5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000]

    if form.validate_on_submit():
        # pd = form.password.data  # could hash
        # user = User(username=form.username.data, email=form.email.data, password=pd)
        # db.session.add(user)
        # db.session.commit()

        # flash(f'Survey erstellt für {form.username.data}!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('main/survey.html', title='Neue Survey', form=form, balance=balance, qualifications=system_qualifications, qualification_percentage_interval=percentage_interval, qualification_integer_list=integer_list, cc_list=ISO3166,)


@app.route("/quali", methods=['GET', 'POST'])
def quali():
    form = QualificationsForm()

    percentage_interval = 5
    integer_list = [1, 5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000]

    return render_template('main/quali.html', title='Neue Survey', qualification_percentage_interval=percentage_interval, qualification_integer_list=integer_list, cc_list=ISO3166, form=form)


@app.route("/qualification/<qtype>")  # replace with parameter in render_template?
def qualification(qtype):
    if qtype == 'system':
        return jsonify(system_qualifications)
    elif qtype == 'custom':
        custom_qualifications = get_custom_qualifications()
        return jsonify(custom_qualifications)
    elif qtype == 'all':
        all_qualifications = system_qualifications + get_custom_qualifications()
        return jsonify(all_qualifications)
    return "no such type"


def split_hit(Hit):
    return


def db_add_microhits(assignments):
    return
