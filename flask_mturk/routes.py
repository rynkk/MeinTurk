from flask import render_template, url_for, flash, redirect
from flask_mturk import app, db, client
from flask_mturk.forms import SurveyForm, QualificationsForm, FieldList, FormField, SelectField, QualificationsFormTest
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

response = client.list_qualification_types(
    MustBeRequestable=False,
    MustBeOwnedByCaller=True,
)['QualificationTypes']


print(response)

system_qualifications = [
    {
        'name': 'Worker_NumberHITsApproved',
        'id': '00000000000000000040',
        'comparators': ['GreaterThan', 'GreaterThanOrEqualTo', 'LessThan', 'LessThanOrEqualTo', 'EqualTo', 'NotEqualTo'],
        'val': 'IntegerValue'  # >=0
    },
    {
        'name': 'Worker_Locale',
        'id': '00000000000000000071',
        'comparators': ['EqualTo', 'NotEqualTo', 'In', 'NotIn'],
        'val': 'LocaleValue'  # https://docs.aws.amazon.com/de_de/AWSMechTurk/latest/AWSMturkAPI/ApiReference_LocaleDataStructureArticle.html
    },
    {
        'name': 'Worker_PercentAssignmentsApproved',
        'id': '000000000000000000L0',
        'comparators': ['GreaterThan', 'GreaterThanOrEqualTo', 'LessThan', 'LessThanOrEqualTo'],
        'val': 'IntegerValue'  # 0<=x<=100
    },
    {
        'name': 'Masters',
        'id': '2ARFPLSP75KLA8M8DH1HTEQVJT3SY6',  # Sandbox
        # 'id': '2F1QJWKUDD8XADTFD2Q0G6UTO95ALH',  # Production
        'comparators': ['Exists']
    },
    {
        'name': 'Worker_Adult',
        'id': '00000000000000000060',
        'comparators': ['EqualTo'],
        'val': 'IntegerValue'  # 1=true(required), 0=false(not required)
    },
]
print("\n")

print(system_qualifications)


@app.route("/")
@app.route("/dashboard")
def dashboard():
    return render_template('main/dashboard.html', surveys="", balance=balance)


@app.route("/survey", methods=['GET', 'POST'])
def survey():
    form = SurveyForm()
    if form.validate_on_submit():
        # pd = form.password.data  # could hash
        # user = User(username=form.username.data, email=form.email.data, password=pd)
        # db.session.add(user)
        # db.session.commit()

        # flash(f'Survey erstellt für {form.username.data}!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('main/survey.html', title='Neue Survey', form=form, balance=balance, qualifications=qualifications)


@app.route("/quali", methods=['GET', 'POST'])
def quali():
    form = QualificationsFormTest()
    # entry1 = QualificationsForm()
    # print(entry1)
    # print(form2)
    # form = QualificationsForm(worker_qualifications=SelectForm())
    # print(form.worker_qualifications.unbound_field)

    # if form2.validate_on_submit():
    #    flash("Validating form")
    return render_template('main/quali.html', title='Neue Survey', form=form)


def split_hit(Hit):
    return


def db_add_microhits(assignments):
    return
