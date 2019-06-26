from flask import render_template, url_for, flash, redirect, jsonify, json, request
from flask_mturk import app, db, client, ISO3166, SYSTEM_QUALIFICATION
from flask_mturk.forms import SurveyForm, QualificationsForm, FieldList, FormField, SelectField, QualificationsSubForm, FlaskForm
from flask_mturk.models import User
import datetime
import time


all_qualifications = None
balance = None
new_balance = client.get_account_balance()['AvailableBalance']
if new_balance != balance:
    print(" Balance changed")
    balance = new_balance


def list_custom_qualifications():
    response = []
    response_page = client.list_qualification_types(
        MustBeRequestable=False,
        MustBeOwnedByCaller=True,
    )
    paginator = response_page.get('NextToken')
    response += response_page['QualificationTypes']
    while paginator is not None:
        response_page = client.list_qualification_types(
            NextToken=paginator,
            MustBeRequestable=False,
            MustBeOwnedByCaller=True,
        )
        paginator = response_page.get('NextToken')
        response += response_page['QualificationTypes']
    return response


def list_all_hits():
    response = []
    response_page = client.list_hits()
    paginator = response_page.get('NextToken')
    response += response_page['HITs']
    while paginator is not None:
        response_page = client.list_hits(NextToken=paginator)
        paginator = response_page.get('NextToken')
        response += response_page['HITs']
    return response


# Helper function to convert timeunit to int #
def seconds_from_string(string):
    if string == 'minutes':
        return 60
    if string == 'hours':
        return 60 * 60
    if string == 'days':
        return 24 * 60 * 60
    return -1


# Helper function to check if string is integer #
def is_number(string):
    try:
        int(string)
        return True
    except ValueError:
        return False


# Helper function to create a qualification object from 3 values #
# https://docs.aws.amazon.com/AWSMechTurk/latest/AWSMturkAPI/ApiReference_QualificationRequirementDataStructureArticle.html #
def create_qualification_object(id, comparator, value, restriction):
    qual_obj = {}
    qual_obj['QualificationTypeId'] = id
    qual_obj['Comparator'] = comparator
    qual_obj['ActionsGuarded'] = restriction

    if value == "None":                   # we are done if second_select did not provide data
        return qual_obj

    if is_number(value):                       # int-> IntegerValues
        int_array = [int(value)]
        qual_obj['IntegerValues'] = int_array
    else:                                       # string-> LocaleValues
        locale_data = {}
        locale_data['Country'] = value
        locale_array = [locale_data]
        qual_obj['LocaleValues'] = locale_array
    return qual_obj


@app.route("/")
@app.route("/dashboard")
def dashboard():
    
    print('getting')
    hits = list_all_hits()
    # TODO
    # sort = request.args.get('sort', 'hitstatus')
    # reverse = (request.args.get('direction', 'asc') == 'desc')
    # table = ItemTable(Item.get_sorted_by(response, sort, reverse),
    #                  sort_by=sort,
    #                  sort_reverse=reverse)
    # print(response["HITs"])
    # items = [dict(Title="Ente", HITStatus="active"), dict(Title="Auto", HITStatus="outtabusinez")]
    # table = ItemTable(response)
    # print(response)
    return render_template('main/dashboard.html', surveys=hits, balance=balance)  # , table=table)


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

    # we need to dynamically change the allowed options for the qual_select
    all_qualifications = SYSTEM_QUALIFICATION + list_custom_qualifications()
    selector_choices = [(qual['QualificationTypeId'], qual["Name"]) for qual in all_qualifications]
    # print(list_custom_qualifications())
    # if post then add choices for each entry of qualifications_select.selects so that form qual_select can validate
    if request.method == "POST":
        for select in form.qualifications_select.selects:
            select.selector.choices = selector_choices

    if form.validate_on_submit():

        # standard fields #

        project_name = form.project_name.data
        title = form.title.data
        description = form.description.data
        keywords = form.keywords.data
        payment_per_worker = str(form.payment_per_worker.data)
        amount_workers = form.amount_workers.data
        
        # question_html =  #form.editor_field.data
        
        html_question_value = """<HTMLQuestion xmlns="http://mechanicalturk.amazonaws.com/AWSMechanicalTurkDataSchemas/2011-11-11/HTMLQuestion.xsd">
                                    <HTMLContent><![CDATA[
                                    <!DOCTYPE html>
                                    <html>
                                    <head>
                                    <meta http-equiv='Content-Type' content='text/html; charset=UTF-8'/>
                                    <script type='text/javascript' src='https://s3.amazonaws.com/mturk-public/externalHIT_v1.js'></script>
                                    </head>
                                    <body>
                                    <form name='mturk_form' method='post' id='mturk_form' action='https://www.mturk.com/mturk/externalSubmit'>
                                    <input type='hidden' value='' name='assignmentId' id='assignmentId'/>
                                    <h1>Answer this question</h1>
                                    <p>asd</p>
                                    <p><textarea name='comment' cols='80' rows='3'></textarea></p>
                                    <p><input type='submit' id='submitButton' value='Submit' /></p></form>
                                    <script language='Javascript'>turkSetAssignmentID();</script>
                                    </body>
                                    </html>
                                    ]]>
                                    </HTMLContent>
                                    <FrameHeight>450</FrameHeight>
                                </HTMLQuestion>"""
        # html_question = HTMLQuestion(html_question_value, 0)

        # seconds fields #
        time_till_expiration = form.time_till_expiration.int_field.data * seconds_from_string(form.time_till_expiration.unit_field.data)
        allotted_time_per_worker = form.allotted_time_per_worker.int_field.data * seconds_from_string(form.allotted_time_per_worker.unit_field.data)
        accept_pay_worker_after = form.accept_pay_worker_after.int_field.data * seconds_from_string(form.accept_pay_worker_after.unit_field.data)

        # qualification fields #
        # https://docs.aws.amazon.com/AWSMechTurk/latest/AWSMturkAPI/ApiReference_QualificationRequirementDataStructureArticle.html#CustomQualificationsandSystemQualifications #
        project_visibility = form.project_visibility.data

        qualifications = []
        for select in form.qualifications_select.selects:
            obj = create_qualification_object(select.selector.data, select.first_select.data, select.second_select.data, project_visibility)
            qualifications.append(obj)

        # master and adult qualification fields #
        must_be_master = form.must_be_master.data
        if must_be_master:
            id = '2ARFPLSP75KLA8M8DH1HTEQVJT3SY6'  # Sandbox
            # id = '2F1QJWKUDD8XADTFD2Q0G6UTO95ALH'  # Production
            obj = create_qualification_object(id, 'Exists', "None", "DiscoverPreviewAndAccept")
            qualifications.append(obj)

        adult_content = form.adult_content.data
        if adult_content:
            id = '00000000000000000060'
            obj = create_qualification_object(id, 'EqualTo', 1, "DiscoverPreviewAndAccept")
            qualifications.append(obj)
        
        print(qualifications)
        # TODO create custom minibatch-qualification and add it to the list, make it ActionsGuarded  "DiscoverPreviewAndAccept" #

        # conditional fields #
        is_starting_instantly = form.starting_date_set.data
        start_date = form.starting_date.data  # convert to right timezone
        is_minibatched = form.minibatch.data
        minibatch_qualification_name = form.qualification_name.data

        # TODO
        #if(form.minibatch.data and form.qualification_name.data == ""):
        #    now = datetime.datetime.now()
        #    print('This is the qualificationname:' + form.project_name.data + "_" + now.strftime("%Y-%m-%dT%H:%M:%S"))

        #if (form.minibatch.data):
        #    create_hit_minibatch()
        #else:
        #    create_hit_standard()

        response = create_hit(amount_workers, accept_pay_worker_after, time_till_expiration, allotted_time_per_worker, payment_per_worker, title, keywords, description, html_question_value, project_name, qualifications)
        print(response)
        print('posted')
        # time.sleep(3)  # wait for mturk endpoint to process the hit

        # hit = HIT(username=form.username.data, email=form.email.data, password=pd)
        # db.session.add(user)
        # db.session.commit()

        # flash(f'Survey erstellt für {form.username.data}!', 'success')
        return redirect(url_for('dashboard'))
    else:
        flash_errors(form)
    return render_template('main/survey.html', title='Neue Survey', form=form, balance=balance, qualifications=all_qualifications, qualification_percentage_interval=percentage_interval, qualification_integer_list=integer_list, cc_list=ISO3166,)


def create_hit_minibatch():
    # TODO
    pass


def create_hit_standard():
    # TODO
    pass


def create_hit(max, autoacc, lifetime, duration, reward, title, keywords, desc, question, reqanno, qualreq):
    # TODO
    response = client.create_hit(
        MaxAssignments=max,
        AutoApprovalDelayInSeconds=autoacc,
        LifetimeInSeconds=lifetime,
        AssignmentDurationInSeconds=duration,
        Reward=reward,
        Title=title,
        Keywords=keywords,
        Description=desc,
        Question=question,
        RequesterAnnotation=reqanno,
        QualificationRequirements=qualreq
    )
    return response


def split_hit(HIT):
    return


def db_add_microhits(assignments):
    return
