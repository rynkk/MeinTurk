from flask import render_template, url_for, flash, redirect, jsonify, json, request
from flask_mturk import app, db, client, ISO3166
from flask_mturk.forms import SurveyForm, QualificationsForm, FieldList, FormField, SelectField, QualificationsSubForm, FlaskForm
from flask_mturk.models import User

all_qualifications = None
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
    response = client.list_hits()["HITs"]
    # sort = request.args.get('sort', 'hitstatus')
    # reverse = (request.args.get('direction', 'asc') == 'desc')
    # table = ItemTable(Item.get_sorted_by(response, sort, reverse),
    #                  sort_by=sort,
    #                  sort_reverse=reverse)
    # print(response["HITs"])
    # items = [dict(Title="Ente", HITStatus="active"), dict(Title="Auto", HITStatus="outtabusinez")]
    # table = ItemTable(response)
    # print(response)
    return render_template('main/dashboard.html', surveys=response, balance=balance)  # , table=table)


def flash_errors(form):
    
    for field, errors in form.errors.items():
        print(errors)
        for error in errors:
            flash(u"Error in the %s field - %s" % (
                getattr(form, field).label.text,
                errors
            ))


@app.route("/survey", methods=['GET', 'POST'])
def survey():
    form = SurveyForm()

    percentage_interval = 5
    integer_list = [1, 5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000]

    all_qualifications = system_qualifications + get_custom_qualifications()
    selector_choices = [(qual['QualificationTypeId'], qual["Name"]) for qual in all_qualifications]  # we need to dynamically change the allowed options for the qual_select
    selector_choices.append(('false', '---SELECT---'))  # select should not be a valid option?

    # if post then add choices for each entry of qualifications_select.selects so that form qual_select can validate
    if request.method == "POST":
        for select in form.qualifications_select.selects:
            select.selector.choices = selector_choices
            
    if form.validate_on_submit():
        # print(form.adult_content.data)
        # pd = form.password.data  # could hash
        # user = User(username=form.username.data, email=form.email.data, password=pd)
        # db.session.add(user)
        # db.session.commit()

        # flash(f'Survey erstellt für {form.username.data}!', 'success')
        return redirect(url_for('dashboard'))
    else:
        flash_errors(form)
    return render_template('main/survey.html', title='Neue Survey', form=form, balance=balance, qualifications=all_qualifications, qualification_percentage_interval=percentage_interval, qualification_integer_list=integer_list, cc_list=ISO3166,)


def create_hit():
    response = client.create_hit(
        MaxAssignments=123,
        AutoApprovalDelayInSeconds=123,
        LifetimeInSeconds=123,
        AssignmentDurationInSeconds=123,
        Reward='string',
        Title='string',
        Keywords='string',
        Description='string',
        Question='string',
        RequesterAnnotation='string',
        QualificationRequirements=[
            {
                'QualificationTypeId': 'string',
                'Comparator': 'LessThan' | 'LessThanOrEqualTo' | 'GreaterThan' | 'GreaterThanOrEqualTo' | 'EqualTo' | 'NotEqualTo' | 'Exists' | 'DoesNotExist' | 'In' | 'NotIn',
                'IntegerValues': [
                    123,
                ],
                'LocaleValues': [
                    {
                        'Country': 'string',
                        'Subdivision': 'string'
                    },
                ],
                'RequiredToPreview': True | False,
                'ActionsGuarded': 'Accept' | 'PreviewAndAccept' | 'DiscoverPreviewAndAccept'
            },
        ],
        UniqueRequestToken='string',
        AssignmentReviewPolicy={
            'PolicyName': 'string',
            'Parameters': [
                {
                    'Key': 'string',
                    'Values': [
                        'string',
                    ],
                    'MapEntries': [
                        {
                            'Key': 'string',
                            'Values': [
                                'string',
                            ]
                        },
                    ]
                },
            ]
        },
        HITReviewPolicy={
            'PolicyName': 'string',
            'Parameters': [
                {
                    'Key': 'string',
                    'Values': [
                        'string',
                    ],
                    'MapEntries': [
                        {
                            'Key': 'string',
                            'Values': [
                                'string',
                            ]
                        },
                    ]
                },
            ]
        },
        HITLayoutId='string',
        HITLayoutParameters=[
            {
                'Name': 'string',
                'Value': 'string'
            },
        ]
    )
    return response


def split_hit(HIT):
    return


def db_add_microhits(assignments):
    return
