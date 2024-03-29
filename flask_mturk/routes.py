import csv
import datetime
import io
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from flask import render_template, url_for, flash, redirect, jsonify, request, Response
from flask_mturk import app, db, babel, ISO3166, SYSTEM_QUALIFICATION
from flask_mturk.forms import SurveyForm, UploadForm, QualificationCreationForm, QualificationsMultiselect, UploadWorkerForm, SingleQualToWorkerForm
from flask_mturk.models import MiniGroup, MiniHIT, TrackedHIT, CachedAnswer, Worker
from flask_babel import gettext as _
from botocore.exceptions import ClientError

from .api_calls import api
from .helper import is_number, is_integer, seconds_from_string

logger = logging.getLogger('routes')


@babel.localeselector
def get_locale():
    if 'language' in request.cookies:
        return request.cookies.get('language')
    return request.accept_languages.best_match(['en', 'de'])


@app.route("/")
@app.route("/dashboard")
def dashboard():
    """Route for the dashboard in which an overview of all HITs is displayed"""

    locale = get_locale()
    balance = api.get_balance()
    hits = api.list_all_hits()
    all_qualifications = SYSTEM_QUALIFICATION + api.list_custom_qualifications()
    groups = MiniGroup.query.filter(MiniGroup.status != 'cached').all()
    order = []

    # Often the API is not quick enough and does not add the created HIT
    # to the list_all_hits, so if it is not there yet we need to add it manually
    createdhit = request.args.get('createdhit')
    if(createdhit is not None):
        new_hit = api.get_hit(createdhit)
        if new_hit not in hits:
            hits.append(new_hit)

    hidden_hits = db.session.query(TrackedHIT.id).filter(TrackedHIT.hidden.is_(True)).all()

    for group in groups:
        batch = {'batch_id': group.id, 'batch_name': group.project_name, 'batch_goal': group.assignments_goal, 'batch_status': group.status, 'hidden': group.hidden, 'hits': []}
        for hit in group.minihits:
            batch['hits'].append({'id': hit.id, 'workers': hit.workers, 'position': hit.position})
        order.append(batch)

    uform = UploadForm()
    logger.info('Serving Dashboard')
    return render_template('main/dashboard.html', title=_('Dashboard'), locale=locale, surveys=hits, ordering=order, balance=balance, uploadform=uform, createdhit=createdhit, quals=all_qualifications, hidden_hits=hidden_hits)


@app.route("/survey", methods=['GET', 'POST'])
def survey():
    """Route for the HIT creation

    Takes care of HIT creation using the Survey-WTForm
    """

    locale = get_locale()
    form = SurveyForm()

    percentage_interval = 5
    integer_list = [1, 5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000]
    balance = api.get_balance()

    # we need to dynamically change the allowed options for the qual_select
    all_qualifications_w_sys = SYSTEM_QUALIFICATION + api.list_custom_qualifications()
    # remove softblock-qualification from the qualification select
    all_qualifications = [q for q in all_qualifications_w_sys if not (q['QualificationTypeId'] == app.config.get('SOFTBLOCK_QUALIFICATION_ID'))]
    # get the softblock name for minibatch-qualification-naming validation purposes
    softblock_name = [q['Name'] for q in all_qualifications_w_sys if q['QualificationTypeId'] == app.config.get('SOFTBLOCK_QUALIFICATION_ID')][0]
    selector_choices = [(qual['QualificationTypeId'], qual["Name"]) for qual in all_qualifications]

    # if post then add choices for each entry of qualifications_select.selects so that form qual_select can validate
    if request.method == "POST":
        if form.payment_per_worker.data > app.config.get('MAX_PAYMENT'):
            logger.warning('Set payment per worker to %s even though only %s is allowed. Aborting HIT-Creation'
                           % (form.payment_per_worker.data, app.config.get('MAX_PAYMENT')))
            return
        for select in form.qualifications_select.selects:
            select.selector.choices = selector_choices

    if form.validate_on_submit():
        logger.info('Submitted form valid! Creating HIT')
        # standard fields #
        project_name = form.project_name.data
        title = form.title.data
        description = form.description.data
        keywords = form.keywords.data
        payment_per_worker = str(form.payment_per_worker.data)
        amount_workers = form.amount_workers.data

        html_question_value = """<?xml version="1.0"?><HTMLQuestion xmlns="http://mechanicalturk.amazonaws.com/AWSMechanicalTurkDataSchemas/2011-11-11/HTMLQuestion.xsd"><HTMLContent><![CDATA[<!DOCTYPE html><html><head><title>HIT</title><meta http-equiv="Content-Type" content="text/html; charset=UTF-8"/><script type='text/javascript' src='https://s3.amazonaws.com/mturk-public/externalHIT_v1.js'></script></head><body><form name="mturk_form" method="post" id="mturk_form" action="https://www.mturk.com/mturk/externalSubmit"><input type="hidden" value="" name="assignmentId" id="assignmentId" />"""\
                              + form.editor_field.data \
                              + """<p class="text-center"><input type="submit" id="submitButton" class="btn btn-primary" value="Submit" /></p></form><script language="Javascript">turkSetAssignmentID();</script></body></html>]]></HTMLContent><FrameHeight>0</FrameHeight></HTMLQuestion>"""

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
        if must_be_master == "yes":
            if app.config.get('SANDBOX'):
                logger.info('Adding Sandbox-Master qualification')
                id = '2ARFPLSP75KLA8M8DH1HTEQVJT3SY6'  # Sandbox
            else:
                logger.info('Adding Live-Master qualification')
                id = '2F1QJWKUDD8XADTFD2Q0G6UTO95ALH'  # Production
            obj = create_qualification_object(id, 'Exists', None, "DiscoverPreviewAndAccept")
            qualifications.append(obj)

        adult_content = form.adult_content.data
        if adult_content:
            logger.info('Adding adult-content qualification')
            id = '00000000000000000060'
            obj = create_qualification_object(id, 'EqualTo', 1, "DiscoverPreviewAndAccept")
            qualifications.append(obj)

        id = app.config.get('SOFTBLOCK_QUALIFICATION_ID')
        logger.info('Adding softblock qualification')
        obj = create_qualification_object(id, "DoesNotExist", None, "DiscoverPreviewAndAccept")
        qualifications.append(obj)

        # conditional fields #
        is_minibatched = form.minibatch.data

        if(is_minibatched):
            if(form.qualification_name.data == ""):
                now = datetime.datetime.now(datetime.timezone.utc)
                logger.info('This is the batch-qualification name: Participated in %s_%s' % (form.project_name.data, now.strftime("%Y-%m-%dT%H:%M:%S")))
                qualification_name = 'Participated In %s_%s' % (form.project_name.data, now.strftime("%Y-%m-%dT%H:%M:%S"))
            else:
                logger.info('This is the batch-qualification name: %s' % form.qualification_name.data)
                qualification_name = form.qualification_name.data

            response = api.create_qualification_type(qualification_name, keywords, "MiniBatch-Qualification for %s" % title)
            qualification_id = response['QualificationTypeId']
            obj = create_qualification_object(qualification_id, "DoesNotExist", None, "DiscoverPreviewAndAccept")
            qualifications.append(obj)

        if(is_minibatched):
            hit_type_id = api.create_hit_type(accept_pay_worker_after, allotted_time_per_worker, payment_per_worker, title, keywords, description, qualifications)
            minigroup = MiniGroup(status='active', project_name=project_name, hidden=False, assignments_submitted=0, assignments_goal=amount_workers, layout=html_question_value, lifetime=time_till_expiration, type_id=hit_type_id, batch_qualification=qualification_id)
            db.session.add(minigroup)
            db.session.flush()
            group_id = minigroup.id
            hit_id = api.create_hit_with_type(hit_type_id, html_question_value, time_till_expiration, 9, 'batch%s' % group_id)['HITId']
            minihit = MiniHIT(group_id=group_id, status='active', position=1, workers=9, id=hit_id)
            db.session.add(minihit)
            db.session.flush()
            add_hits_to_db(group_id, amount_workers - 9)  # -9 because we already created one HIT with 9 workers
            db.session.commit()
        else:
            hit = api.create_hit(amount_workers, accept_pay_worker_after, time_till_expiration, allotted_time_per_worker, payment_per_worker, title, keywords, description, html_question_value, qualifications)
            hit_type_id = hit['HITTypeId']
            hit_id = hit['HITId']
            tracked_hit = TrackedHIT(id=hit_id, hidden=False, active=True)
            db.session.add(tracked_hit)
            db.session.commit()

        logger.info('Redirecting to Dashboard')
        return redirect(url_for('dashboard', createdhit=hit_id))
    else:
        logger.warning('Submitted form not valid, aborting and flashing errors')
        flash_errors(form)
    logger.info('Serving Survey')
    return render_template('main/survey.html', locale=locale, title=_('New Survey'), form=form, balance=balance, qualifications=all_qualifications, qualification_percentage_interval=percentage_interval, qualification_integer_list=integer_list, cc_list=ISO3166, max_payment=app.config.get('MAX_PAYMENT'), softblock_name=softblock_name)


@app.route("/qualifications", methods=['GET', 'POST'])
def qualifications_page():
    """Route for the qualifications page where you can delete or create qualifications"""

    locale = get_locale()
    form = QualificationCreationForm()
    if request.method == 'GET':
        balance = api.get_balance()
        qualifications = api.list_custom_qualifications()
        # remove softblock-qualification
        qualifications = [q for q in qualifications if not (q['QualificationTypeId'] == app.config.get('SOFTBLOCK_QUALIFICATION_ID'))]
        logger.info('Serving Qualification-List')
        return render_template('main/qualification_list.html', title=_('Qualifications'), locale=locale, balance=balance, qualifications=qualifications, form=form)

    if request.method == 'POST':
        logger.info('Creating qualification')
        if form.validate():
            name = form.name.data
            desc = form.desc.data
            keywords = form.keywords.data
            autogranted = form.auto_granted.data
            autogranted_val = form.auto_granted_value.data
            try:
                qual = api.create_qualification_type(name, keywords, desc, autogranted, autogranted_val)
                return jsonify({'success': True, 'data': qual}), 201
            except ClientError as err:
                logger.exception('Could not create Qualification. Aborting')
                return jsonify({'success': False, 'error': err.response['Error']['Message']}), 409
        logger.info('Qualification contains non-valid data. Aborting')
        return jsonify({'success': False, 'error': form.errors}), 418


@app.route("/worker")
def worker_page():
    """Route for the worker page where you can see all workers that worked for you, assign qualifications and softblock them """

    locale = get_locale()
    balance = api.get_balance()
    workers_queried = Worker.query.all()

    softblocked_workers = api.list_workers_with_qualification_type(app.config.get('SOFTBLOCK_QUALIFICATION_ID'))

    workers = []
    for w in workers_queried:
        worker = {'id': w.id, 'no_ass': w.no_assignments, 'no_app': w.no_approved,
                  'no_rej': w.no_rejected, 'bonus_total': w.bonus_total,
                  'softblocked': False, 'last_submission': w.last_completed}
        if any(w.id == worker['WorkerId'] for worker in softblocked_workers):
            worker['softblocked'] = True

        workers.append(worker)

    qualifications = api.list_custom_qualifications()
    selector_choices = [(q['QualificationTypeId'], q["Name"]) for q in qualifications if not (q['QualificationTypeId'] == app.config.get('SOFTBLOCK_QUALIFICATION_ID'))]

    qual_select = QualificationsMultiselect()
    qual_select.multiselect.choices = selector_choices

    single_qual = SingleQualToWorkerForm()
    single_qual.select.choices = selector_choices
    fileselect = UploadWorkerForm()
    logger.info('Serving Worker Page')
    return render_template('main/worker_list.html', title=_('Workers'), locale=locale, balance=balance, workers=workers, singleselect=single_qual, multiselect=qual_select, fileselect=fileselect)


@app.route("/export_workers", methods=['POST'])
def worker_export():
    """Route to provide a CSV with the necessary Worker and Qualification Fields"""

    form = QualificationsMultiselect()
    qualifications = api.list_custom_qualifications()
    selector_choices = [(q['QualificationTypeId'], q["Name"]) for q in qualifications if not (q['QualificationTypeId'] == app.config.get('SOFTBLOCK_QUALIFICATION_ID'))]
    form.multiselect.choices = selector_choices
    if form.validate_on_submit():
        fieldnames = ['WorkerId']
        for q in form.multiselect.data:
            name = [quals[1] for quals in selector_choices if quals[0] == q][0]
            fieldnames.append(q + "#" + name)

        si = io.StringIO()
        csv_writer = csv.DictWriter(si, fieldnames)
        csv_writer.writeheader()

        workers = Worker.query.all()
        for worker in workers:
            row = {'WorkerId': worker.id}
            csv_writer.writerow(row)

        return Response(si.getvalue(), mimetype='text/csv', headers={"Content-Disposition": "attachment;filename=worker_export"})
    return jsonify({'success': False, 'error': _('Could not validate the selected Qualifications! Did you delete any of them before trying to export the CSV?')}), 400


@app.route("/upload_workers", methods=['POST'])
def upload_workers():
    """Route to provide a CSV with the necessary Worker and Qualification Fields"""

    form = UploadWorkerForm()

    if form.validate_on_submit():
        csvfile = form.file.data
        csvdata = io.StringIO(csvfile.read().decode('utf-8'))

        csvreader = csv.DictReader(csvdata)
        # checking if the csv contains valid data
        errors = {}
        data_exists = False
        for index, row in enumerate(csvreader, 1):
            try:
                row['WorkerId']
            except KeyError as e:
                logger.exception('Uploaded CSV contains not valid headers')
                return jsonify({'success': False, 'errortype': 'main', 'errors': {'main': _('CSV header not formatted properly: </br> Missing header %s') % e}}), 422

            qualifications = iter(row)
            # skipping workerid
            next(qualifications)
            for q in qualifications:
                if not q:
                    errors.setdefault(index, []).append(_('Qualification Header missing'))
                value = row[q]
                if value and not is_integer(value):
                    errors.setdefault(index, []).append(_('Qualification Values must be Integers; "%s" was entered!') % value)
                elif is_integer(value) and int(value) < 0:
                    errors.setdefault(index, []).append(_('Qualification Values must be positive (or 0); "%s" was entered!') % value)
                elif is_integer(value) and int(value) >= 0:
                    # All ok
                    data_exists = True

        if errors:
            return jsonify({'success': False, 'errortype': 'document', 'errors': errors}), 422

        if not data_exists:
            return jsonify({'success': False, 'errortype': 'main', 'errors': {'main': _('No processable Data in CSV!')}}), 422

        warnings = {}
        csvdata.seek(0)
        csvreader = csv.DictReader(csvdata)
        for index, row in enumerate(csvreader, 1):
            workerid = row['WorkerId']

            qualifications = iter(row)
            # skipping workerid
            next(qualifications)
            for q in qualifications:
                value = row[q]
                qualid = q.split('#')[0]
                if is_integer(value) and int(value) >= 0:
                    error = api.associate_qualification_with_worker(workerid, qualid, int(value))
                    if error is not None:
                        warnings.setdefault(index, []).append(_('Could not associate qualification: %s') % error)
                elif value:
                    warnings.setdefault(index, []).append(_('Qualification Values must be Integers and positive (or 0); "%s" was entered!') % value)

        return jsonify({'success': True, 'warnings': warnings})
    return jsonify({'success': False, 'errortype': 'form', 'errors': form.errors}), 400


@app.route("/cached")
def cached_page():
    """Route for the cached page where you can see all archived Batches and download their results"""

    locale = get_locale()
    balance = api.get_balance()
    groups = MiniGroup.query.filter(MiniGroup.status == 'cached').all()
    cached_batches = []
    for group in groups:
        batch = {'name': group.project_name, 'id': group.id, 'goal': group.assignments_goal, 'submitted': group.assignments_submitted}
        cached_batches.append(batch)

    return render_template('main/cached_list.html', title=_('Cached Batches'), locale=locale, balance=balance, batches=cached_batches)


@app.route("/cache_batch/<int:batchid>", methods=['DELETE'])
def cache_batch(batchid):
    """Route that deleted the specified batch from the AWS-Endpoint and archives it locally"""

    group = MiniGroup.query\
        .filter(MiniGroup.id == batchid)\
        .filter(MiniGroup.status != 'cached')\
        .one_or_none()
    if group is None:
        return jsonify({'success': False, 'error': _('Not found')}), 404

    hits = MiniHIT.query.filter(MiniHIT.group_id == group.id).all()
    ids = []
    for hit in hits:
        # Check if there are still pending or non approved/rejected Answers
        if hit.id is None:
            # if hit is queued but not published, delete them
            db.session.delete(hit)
            continue
        response = api.get_hit(hit.id)
        ids.append(hit.id)

        if response['NumberOfAssignmentsPending'] > 0:
            return jsonify({'success': False, 'error': _('Batch still has pending assignments.')}), 423
        if response['MaxAssignments'] != response['NumberOfAssignmentsCompleted'] + response['NumberOfAssignmentsAvailable']:
            return jsonify({'success': False, 'error': _('Batch still has non-completed assignments.')}), 423
        if response['HITStatus'] != 'Reviewable':
            return jsonify({'success': False, 'error': _('Cannot cache Batch with active HITs.')}), 423
        assignments = get_assignments(hit.id, False)
        bonus_payments = api.list_bonus_payments_for_hit(hit.id)
        for a in assignments:
            approved = True if a['AssignmentStatus'] == 'Approved' else False
            bonus_obj = next((payment for payment in bonus_payments if payment['WorkerId'] == a['WorkerId'] and payment['AssignmentId'] == a['AssignmentId']), None)

            # Convert bonus to Cents to prepare it for the DB
            if(bonus_obj):
                bonus = int(float(bonus_obj['BonusAmount']) * 100)
                reason = bonus_obj['Reason']
            else:
                bonus = ""
                reason = ""
            time_taken = (a['SubmitTime'] - a['AcceptTime']).total_seconds()

            ca = CachedAnswer(hit_id=hit.id, assignment_id=a['AssignmentId'],
                              worker_id=a['WorkerId'], answer=a['Answer'],
                              approved=approved, bonus=bonus, reason=reason,
                              accept_date=a['AcceptTime'], time_taken=time_taken)
            db.session.add(ca)

        hit.status = 'cached'
    group.status = 'cached'
    db.session.commit()
    api.delete_hits(ids)
    return jsonify({'success': True}), 200


@app.route("/assignment_goal/<int:batchid>")
@app.route("/assignment_goal/<int:batchid>/<int:goal>", methods=['PATCH'])
def update_goal(batchid, goal=None):
    """Route to update or return the current assignment goal of the specified Batches """

    group = MiniGroup.query.filter(MiniGroup.id == batchid).one_or_none()
    if not group:
        return jsonify({'success': False, 'error': _('Could not find Batch with id %s.') % batchid}), 404

    if request.method == 'GET':
        return jsonify({'success': True, 'goal': group.assignments_goal}), 200
    elif request.method == 'POST':
        group.assignments_goal = goal
        db.session.commit()
        return jsonify({'success': True, 'goal': goal}), 200


@app.route("/export/<int:id>/<type_>")
@app.route("/export/<awsid:id>/<type_>")
def export(id, type_):
    """Route that exports either all or only submitted results of normal and batched HITs"""

    batched = is_number(id)
    fieldnames = ['HITId', 'AssignmentId', 'WorkerId', 'Status', 'Answer', 'TimeTaken', 'Approve', 'Reject', 'RejectionMessage', 'Bonus', 'Reason', 'Softblock', 'FollowUpQualificationID', 'FollowUpValue']

    if type_ == 'all':
        assignments = get_assignments(id, batched)  # Add submitted, rejected and approved Assignments to export
        # probably add payments for every id here
        softblocked_workers = api.list_workers_with_qualification_type(app.config.get('SOFTBLOCK_QUALIFICATION_ID'))
        filename = "results_all.csv"

    elif type_ == 'submitted':
        assignments = get_assignments(id, batched, ['Submitted'])  # Add only submitted Assignments to export
        filename = "results_new.csv"

    si = io.StringIO()
    csv_writer = csv.DictWriter(si, fieldnames)
    csv_writer.writeheader()

    for a in assignments:
        row = {'HITId': a['HITId'], 'AssignmentId': a['AssignmentId'], 'WorkerId': a['WorkerId'],
               'Status': a['AssignmentStatus'], 'Answer': a['Answer']}
        time_taken = int((a['SubmitTime'] - a['AcceptTime']).total_seconds())
        row['TimeTaken'] = time_taken
        if 'RequesterFeedback' in a:
            row['RejectionMessage'] = a['RequesterFeedback']
        else:
            row['RejectionMessage'] = ''

        if a['AssignmentStatus'] == 'Submitted':
            csv_writer.writerow(row)
        else:
            # Might be faster to list payments for entire HIT/entire MiniGroup
            bonus = api.list_bonus_payments_for_assignment(a['AssignmentId'])

            if len(bonus) == 1:
                bonus = bonus[0]
                row['Bonus'] = bonus['BonusAmount']
                row['Reason'] = bonus['Reason']

            if a['AssignmentStatus'] == 'Approved':
                row['Approve'] = 'x'
            else:
                row['Reject'] = 'x'

            if any(worker['WorkerId'] == a['WorkerId'] for worker in softblocked_workers):
                row['Softblock'] = 'x'
            csv_writer.writerow(row)
    return Response(si.getvalue(), mimetype='text/csv', headers={"Content-Disposition": "attachment;filename=%s" % filename})


@app.route("/export_cached/<int:id>")
def export_cached(id):
    """Route that exports the assignment results of a archived Batch"""

    group = MiniGroup.query\
                     .filter(MiniGroup.id == id)\
                     .filter(MiniGroup.status == 'cached')\
                     .one_or_none()
    if(group is None):
        return jsonify({'success': False}), 404

    softblocked_workers = api.list_workers_with_qualification_type(app.config.get('SOFTBLOCK_QUALIFICATION_ID'))
    assignments = []

    for hit in group.minihits:
        for answer in hit.answers:
            a = {'HITId': answer.hit_id, 'AssignmentId': answer.assignment_id,
                 'WorkerId': answer.worker_id, 'Answer': answer.answer,
                 'TimeTaken': answer.time_taken, 'Reason': answer.reason}

            if answer.bonus != "" and answer.bonus:
                a['Bonus'] = answer.bonus / 100,

            if answer.approved:
                a['Status'] = 'Approved'
                a['Approve'] = 'x'
            else:
                a['Status'] = 'Rejected'
                a['Reject'] = 'x'

            if any(worker['WorkerId'] == answer.worker_id for worker in softblocked_workers):
                a['Softblock'] = 'x'
            assignments.append(a)

    si = io.StringIO()
    fieldnames = ['HITId', 'AssignmentId', 'WorkerId', 'Status', 'Answer', 'TimeTaken', 'Approve', 'Reject', 'Bonus', 'Reason', 'Softblock']

    csv_writer = csv.DictWriter(si, fieldnames)
    csv_writer.writeheader()

    for row in assignments:
        csv_writer.writerow(row)

    return Response(si.getvalue(), mimetype='text/csv', headers={"Content-Disposition": "attachment;filename=result_cached.csv"})


@app.route("/upload", methods=['POST'])
def upload():
    """Route that evaluates the uploaded CSV and takes actions based on the input

    First it logic checks all entered data and after that it does AWS-API interaction based on the validated data.
    """

    form = UploadForm()

    if form.validate_on_submit():
        logger.info('Uploadeded CSV. Checking if valid.')

        csvfile = form.file.data
        csvdata = io.StringIO(csvfile.read().decode('utf-8'))

        csvreader = csv.DictReader(csvdata)
        # checking if the csv contains valid data
        errors = {}
        checked_fuquals = []
        assignments = get_assignments(form.hit_identifier.data, form.hit_batched.data)  # maybe make status Submitted
        if not assignments:
            return jsonify({'success': False, 'errortype': 'main', 'errors': {'main': _('No Assignments found.')}}), 404
        for index, row in enumerate(csvreader, 1):
            try:
                hitid = row['HITId']
                assignmentid = row['AssignmentId']
                workerid = row['WorkerId']
                assignmentstatus = row['Status']
                approve = row['Approve']
                reject = row['Reject']
                row['RejectionMessage']
                bonus = row['Bonus']
                reason = row['Reason']
                row['Softblock']
                fuqual = row['FollowUpQualificationID']
                fuvalue = row['FollowUpValue']
            except KeyError as e:
                logger.exception('Uploaded CSV contains not valid headers')
                return jsonify({'success': False, 'errortype': 'main', 'errors': {'main': _('CSV header not formatted properly: </br> Missing header %s') % e}}), 422

            if approve and reject:
                errors.setdefault(index, []).append(_('Approve and Reject are both set.'))
            if not approve and not reject:
                errors.setdefault(index, []).append(_('Approve and Reject are both not set.'))

            valid_hit_assignment_worker = False
            for assignment in assignments:
                if assignment['AssignmentId'] == assignmentid\
                        and assignment['WorkerId'] == workerid\
                        and assignment['HITId'] == hitid:
                    valid_hit_assignment_worker = True

                    # No duplicates allowed
                    if 'DuplicateCheck' in assignment:
                        errors.setdefault(index, []).append(_('Duplicate HIT/Assignment/Worker combination.'))
                    else:
                        assignment['DuplicateCheck'] = True
            if assignmentstatus not in ['Approved', 'Submitted', 'Rejected']:
                errors.setdefault(index, []).append(_('Non-valid Assignment status: "%s".') % assignmentstatus)
            if not valid_hit_assignment_worker:
                errors.setdefault(index, []).append(_('Non-valid HIT/Assignment/Worker combination.'))
            if bonus and not is_number(bonus):
                errors.setdefault(index, []).append(_('Bonus not a valid number.'))
            if is_number(bonus) and float(bonus) > app.config.get('MAX_BONUS'):
                errors.setdefault(index, []).append(_('Bonus is too high. MAX: %s.') % app.config.get('MAX_BONUS'))
            if bonus and not reason:
                errors.setdefault(index, []).append(_('Bonus assigned but no reason given.'))
            if fuqual and fuqual not in checked_fuquals:
                checked_fuquals.append(fuqual)
                error = api.get_qualification_type(fuqual)
                if error is not None:
                    errors.setdefault(index, []).append(_('Could not get Qualification %s, are you sure that is the right ID?') % fuqual)
            if fuvalue and not is_integer(fuvalue):
                errors.setdefault(index, []).append(_('FollowUpQualifications Value must be an integer!') % fuvalue)
            if fuvalue and is_integer(fuvalue) and int(fuvalue) < 0:
                errors.setdefault(index, []).append(_('FollowUpQualifications Value must be greater than or equal to 0!') % fuvalue)

        if errors:
            logger.warning(' CSV contained errors. Showing errors to user and aborting.')
            return jsonify({'success': False, 'errortype': 'document', 'errors': errors}), 422

        logger.info(' CSV seems valid. Trying to do API-Calls now')
        total_approved = 0
        total_rejected = 0
        total_softblocked = 0
        total_bonus = 0.0

        # Going back to beginning of CSV if data appeared valid
        warnings = {}
        csvdata.seek(0)
        csvreader = csv.DictReader(csvdata)
        for index, row in enumerate(csvreader, 1):
            if row['Status'] != 'Submitted':
                # Skipping line if already approved/rejected
                continue
            hitid = row['HITId']
            assignmentid = row['AssignmentId']
            workerid = row['WorkerId']
            approve = row['Approve']
            reject = row['Reject']
            rejection_message = row['RejectionMessage']
            bonus = row['Bonus']
            reason = row['Reason']
            softblock = row['Softblock']
            fuqual = row['FollowUpQualificationID']
            fuvalue = row['FollowUpValue']
            unique_token_bonus = assignmentid + workerid

            logger.info('Worker: %s' % workerid)
            worker = Worker.query.filter(Worker.id == workerid).one_or_none()
            if worker is None:
                logger.info('New Worker! Adding to Database')
                # Normally the worker will be created once a HIT is finished (in update_mini_hits)
                # If the results are uploaded while the HIT is still assignable we have to create the worker now.
                worker = Worker(id=workerid, no_assignments=0)
                db.session.add(worker)
                db.session.flush()

            if approve:
                error = api.approve_assignment(assignmentid)
                if error is None:
                    logger.info('Updating Database worker-entry for his assignment being approved')
                    total_approved += 1
                    worker.no_approved += 1
                else:
                    warnings.setdefault(index, []).append(_('Could not approve assignment, maybe it was auto-approved already?'))
            if reject:
                if rejection_message == '':  # if rejection message not set, set it to default
                    rejection_message = app.config.get('DEFAULT_REJECTION_MESSAGE')

                error = api.reject_assignment(assignmentid, rejection_message)

                if error is None:
                    logger.info('Updating Database worker-entry for his assignment being rejected')
                    total_rejected += 1
                    worker.no_rejected += 1
                else:
                    warnings.setdefault(index, []).append(_('Could not reject assignment, maybe it was auto-approved already?'))
            if bonus:
                error = api.send_bonus(workerid, assignmentid, bonus, reason, unique_token_bonus)
                if error is None:
                    logger.info('Updating Database worker-entry to accomodate paid bonus')
                    total_bonus += float(bonus)
                    worker.bonus_total += int(float(bonus) * 100)
                else:
                    warnings.setdefault(index, []).append(_('Could not send bonus. You can only send one bonus per Assignment!'))

            if softblock:
                # errorhandling for softblock
                softblock_id = app.config.get('SOFTBLOCK_QUALIFICATION_ID')
                error = api.associate_qualification_with_worker(workerid, softblock_id)
                if error is None:
                    logger.info('Softblocking worker')
                    total_softblocked += 1
                    worker.softblocked = True
                else:
                    warnings.setdefault(index, []).append(_('Could not send softblock worker %s, you will have to do it manually now.') % workerid)

            if fuqual:
                if not fuvalue:
                    warnings.setdefault(index, []).append(_('FollowUpValue not specified, setting it to 1.'))
                    fuvalue = 1

                error = api.associate_qualification_with_worker(workerid, fuqual, int(fuvalue))
                if error is not None:
                    warnings.setdefault(index, []).append(_('Could not send softblock worker %s, you will have to do it manually now.') % workerid)

        db.session.commit()

        data = {}
        data['approved'] = total_approved
        data['rejected'] = total_rejected
        data['softblocked'] = total_softblocked
        data['bonus'] = total_bonus

        return jsonify({'success': True, 'data': data, 'warnings': warnings}), 200

    return jsonify({'success': False, 'errortype': 'form', 'errors': form.errors}), 400


@app.route("/db/toggle_hit_visibility/<awsid:id>", methods=['PATCH'])
@app.route("/db/toggle_hit_visibility/<int:id>/<batched>", methods=['PATCH'])
def toggle_hit_visibility(id, batched=False):
    """Route that toggles the dashboard-visibility of normal or batched HITs"""

    batched = (batched == 'True' or batched == 'true')
    if batched:
        logger.info('Hiding Batch %s', id)
        group = MiniGroup.query.filter(MiniGroup.id == id).one_or_none()
        if group:
            group.hidden = not group.hidden
            logger.info('Hidden of Batch %s set to %s' % (id, group.hidden))
            hidden = group.hidden
        else:
            logger.warning('No Batch with ID %s.' % id)
            return jsonify({'success': False, 'error': _('No Batch with ID %s.') % id}), 404
    else:
        logger.info('Hiding HIT %s', id)
        hit = TrackedHIT.query.filter(TrackedHIT.id == id).one_or_none()
        if hit is None:
            logger.warning('No HIT with ID %s', id)
            return jsonify({'success': False, 'error': _('No HIT with ID %s exists in Database.') % id}), 404
        else:
            logger.info('Hidden of HIT %s set to %s' % (id, not hit.hidden))
            hidden = not hit.hidden
            hit.hidden = not hit.hidden

    db.session.commit()
    return jsonify({'success': True, 'hidden': hidden}), 200


def get_assignments(id, batched, status=None):
    """Helper function that get assignments of the specified status formats their answers and returns them"""

    if(batched):
        hits = db.session.query(MiniHIT.id)\
            .filter(MiniHIT.group_id == id)\
            .filter(MiniHIT.id.isnot(None)).all()
        ids = []
        for hit in hits:
            ids.append(hit.id)
        assignments = api.list_assignments_for_hits(ids, status)
    else:
        assignments = api.list_assignments_for_hit(id, status)

    for assignment in assignments:

        answer_xml = assignment['Answer']
        start = answer_xml.index("<FreeText>") + len("<FreeText>")
        end = answer_xml.index("</FreeText>")
        assignment['Answer'] = answer_xml[start:end]

    return assignments


@app.route("/list_assignments/<awsid:id>")
@app.route("/list_assignments/<int:id>/<batched>")
def list_assignments(id, batched=False):
    """Route that returns all assignments of normal or batched HITs"""

    assignments = get_assignments(id, batched)
    return jsonify(assignments)


@app.route('/db/delete-queued/<int:group_id>/<int:position>', methods=['DELETE'])
def delete_queued_from_db(group_id, position):
    """Route that deletes a queued MiniHIT of the specified group at the specified position"""

    logger.info('Deleting of queued MiniHIT of Batch %s at position %s' % (group_id, position))
    to_delete = MiniHIT.query\
        .filter(MiniHIT.status != 'cached')\
        .filter(MiniHIT.group_id == group_id)\
        .filter(MiniHIT.position == position).one_or_none()
    if to_delete is None:
        logger.warning('MiniHIT not found!')
        return jsonify({'success': False, 'type': 'not_found', 'error': _('No MiniHIT at position %s of Group %s found!') % (position, group_id)}), 404

    unnecessary_keys = ['AssignmentDurationInSeconds', 'AutoApprovalDelayInSeconds', 'Description', 'HITGroupId',
                        'Keywords', 'QualificationRequirements', 'Question', 'Reward', 'Title']

    if to_delete.id is not None:
        logger.info('MiniHIT was already published!')
        hit = api.get_hit(to_delete.id)
        hit['workers'] = to_delete.workers
        hit['position'] = to_delete.position
        for key in unnecessary_keys:
            if key in hit:
                del hit[key]
        return jsonify({'success': False, 'type': 'locked', 'hit': hit, 'error': _('MiniHIT at position %s of Group %s was already published!') % (position, group_id)}), 423

    db.session.delete(to_delete)

    # We need to correct the indice of the following HITs to maintain database integrity
    to_index = MiniHIT.query\
        .filter(MiniHIT.group_id == group_id)\
        .filter(MiniHIT.position > position).all()

    for hit in to_index:
        hit.position -= 1

    logger.info('Success!')
    db.session.commit()
    return jsonify({'success': True}), 200


@app.route('/db/toggle_softblock/<awsid:workerid>', methods=['PATCH'])
def toggle_softblock_route(workerid):
    sb_id = app.config.get('SOFTBLOCK_QUALIFICATION_ID')
    try:
        api.disassociate_qualification_from_worker(workerid, sb_id)
        logger.info('Removed softblock from worker %s' % workerid)
        return jsonify({'success': True, 'status': False}), 200
    except ClientError:
        try:
            api.associate_qualification_with_worker(workerid, sb_id)
            logger.info('Added softblock to worker %s' % workerid)
            return jsonify({'success': True, 'status': True}), 200
        except ClientError as ce:
            logger.exception('An error occured trying to toggle softblock of worker %s' % workerid)
            return jsonify({'success': False, 'error': ce['Error']['Message']}), 423
    return jsonify({'success': False, 'error': _('Something weird happened.')}), 423


@app.route('/db/delete_cached/<int:group_id>', methods=['DELETE'])
def delete_cached(group_id):
    """Route that deletes the specified cached batch"""

    logger.info('Deleting cached Batch %s' % group_id)

    batch = MiniGroup.query.filter(MiniGroup.id == group_id).one_or_none()
    if(batch is None):
        logger.warning('Cached Batch %s does not exist.' % group_id)
        return jsonify({'success': False, 'error': _('No Batch with ID.')}), 404
    if(batch.status != 'cached'):
        logger.warning('Batch at position %s is not cached.' % group_id)
        return jsonify({'success': False, 'error': _('Batch is not cached.')}), 423
    db.session.delete(batch)
    db.session.commit()
    logger.info('Success')
    return jsonify({'success': True}), 200


@app.route('/db/toggle_group_status/<int:group_id>', methods=['PATCH'])
def toggle_group_status(group_id):
    """Route that toggles the specified groups status (active or inactive)"""

    logger.info('Toggling Batch %s status' % group_id)

    group = MiniGroup.query.filter(MiniGroup.id == group_id)\
                           .filter(MiniGroup.status != 'cached').one_or_none()
    if(group is None):
        logger.warning('Batch %s does not exist' % group_id)
        return jsonify({'success': False, 'error': _('Group does not exist.')}), 404
    if group.status == 'active':
        group.status = 'inactive'
    else:
        group.status = 'active'
    status = group.status
    db.session.commit()
    logger.info('Success. Set status to %s' % status)
    return jsonify({'success': True, 'status': status}), 200


@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({'success': False, 'error': error}), 500


def create_qualification_object(id, comparator, value, restriction):
    """ Helper function to create qualification objects according to the AWS specifications

    The AWS specifications for qualifications are found here:
    https://docs.aws.amazon.com/AWSMechTurk/latest/AWSMturkAPI/ApiReference_QualificationRequirementDataStructureArticle.html
    """

    qual_obj = {}
    qual_obj['QualificationTypeId'] = id
    qual_obj['Comparator'] = comparator
    qual_obj['ActionsGuarded'] = restriction

    if value is None or comparator in ['Exists', 'DoesNotExist']:                   # we are done if second_select did not provide data
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


def flash_errors(form):
    """ Simple script to flash form errors to the frontend """

    for field, errors in form.errors.items():
        for error in errors:
            flash(u"Error in the %s field - %s" % (
                getattr(form, field).short_name,
                errors
            ))


# Doesnt commit
def add_hits_to_db(groupid: int, assignments: int) -> None:
    """ Adds queued MiniHITs to a Minigroup

    This will split the assignments into parts of 9 (the last one might be less)
    and adds these parts as queued MiniHITs to the MiniGroup specified.

    Note: this function will not commit the changed made.
    """

    max_pos = db.session.query(db.func.max(MiniHIT.position))\
        .filter(MiniHIT.group_id == groupid)\
        .filter(MiniHIT.status != 'cached').scalar()
    if max_pos is None:
        return "Error"
    max_pos += 1

    part = assignments % 9
    full = int((assignments - part) / 9)
    logger.info("Adding %s new queued HITs to DB a 9 Workers" % full)
    for i in range(full):
        minihit = MiniHIT(group_id=groupid, status='inactive', position=max_pos + i, workers=9, id=None)
        db.session.add(minihit)
    if part > 0:
        logger.info("Adding new queued HITs to DB with %s Workers" % part)
        minihit = MiniHIT(group_id=groupid, status='inactive', position=max_pos + full, workers=part, id=None)
        db.session.add(minihit)


def update_mini_hits() -> None:
    """Takes care of publishing new HITs if some expired and syncs with the DB

    Iterates over all active Batches(=MiniGroups) to check if their active HIT is done or not.

    If the active HIT is done its details are fetched from the AWS endpoint and integrated into the local DB.
    Additionally all workers that are part of that HIT will be granted a batch qualification to prevent multiple
    participations within the same batch. These workers are also saved into the local DB.

    The next (queued) HIT will be published. If there is no next HIT we check whether the submission goal of the batch is reached.
    If not we add additional queued HITs and publish the first one.
    If yes we set the batch to inactive.
    """

    logger.info('Updating MiniHITs')
    query = db.session.query(MiniGroup, MiniHIT)\
        .filter(MiniGroup.id == MiniHIT.group_id)\
        .filter(MiniHIT.status == 'active')\
        .filter(MiniGroup.status == 'active').all()

    for row in query:
        active_hit_id = row.MiniHIT.id
        active_hit = api.get_hit(active_hit_id)
        logger.info("Checking %s with HITStatus %s, from Group %s " % (active_hit_id, active_hit['HITStatus'], row.MiniGroup.id))

        # Reviewable: if (expired AND pending==0) or (maxassignments-available+pending == 0)
        if(active_hit['HITStatus'] == 'Reviewable'):

            # Need to get Done HIT to check how many Assignments were submitted
            hit = api.get_hit(active_hit_id)
            max_ass = hit['MaxAssignments']
            pending_ass = hit['NumberOfAssignmentsPending']  # Should always be 0 due to Reviewable Status (adding just in case)
            available_ass = hit['NumberOfAssignmentsAvailable']
            submitted = max_ass - (available_ass + pending_ass)

            if available_ass + pending_ass == 0:
                logger.info("*** All Assignments were submitted ***")
            else:
                logger.info("*** HIT expired ***")

            logger.info("*** Adding #submittedAssignments to MiniGroup: %s ***" % submitted)
            row.MiniGroup.assignments_submitted += submitted
            logger.info("*** Granting workers the batch qualification ***")
            result = api.grant_qualifications_for_hit(active_hit_id, row.MiniGroup.batch_qualification)
            if result['success']:
                # workers: All workers that have worked for you before
                workers = Worker.query.filter(Worker.id.in_(result['workers'])).all()
                worker_ids = []
                for worker in workers:
                    worker_ids.append(worker.id)
                    worker.no_assignments += 1
                    worker.last_completed = datetime.datetime.now(datetime.timezone.utc)
                    logger.info('*** increasing worker %s assignments by 1***' % worker.id)
                # diff: All workers that have never worked for you before
                diff = [x for x in result['workers'] if x not in worker_ids]
                # adding these workers to the DB
                for id_ in diff:
                    logger.info('*** Adding missing worker %s to db***' % id_)
                    db.session.add(Worker(id=id_))

            logger.info("*** Creating new MiniHIT ***")
            new_position = row.MiniHIT.position + 1

            # Fetching Group-specific data that is shared between MiniHITs and is needed for the new MiniHIT
            group_id = row.MiniGroup.id
            hittypeid = row.MiniGroup.type_id
            question = row.MiniGroup.layout
            lifetime = row.MiniGroup.lifetime

            # Getting the new MiniHIT-DB-entry
            new_mini_hit = MiniHIT.query.filter(MiniHIT.position == new_position)\
                                        .filter(MiniHIT.group_id == group_id)\
                                        .one_or_none()

            # Checking if there is a following MiniHIT
            if(new_mini_hit is None):
                logger.info("No queued HIT left. Checking if we reached the submission goal...")
                submissions = row.MiniGroup.assignments_submitted
                goal = row.MiniGroup.assignments_goal
                if submissions >= goal:
                    logger.info("Goal reached: Submitted: %s, Goal: %s. Making Group inactive" % (submissions, goal))
                    row.MiniGroup.status = 'inactive'
                    continue
                else:
                    needed = goal - submissions
                    logger.info("Goal not reached: Submitted: %s, Goal: %s, Needed: %s." % (submissions, goal, needed))
                    add_hits_to_db(group_id, needed)
                    db.session.flush()
                    # Getting the new MiniHIT-DB-entry
                    new_mini_hit = \
                        MiniHIT.query.filter(MiniHIT.position == new_position)\
                        .filter(MiniHIT.group_id == group_id)\
                        .one()

            # Because the current MiniHIT is expired we set it to inactive
            row.MiniHIT.status = 'inactive'

            workers = new_mini_hit.workers

            # Creating a new HIT with the assigned attributes and saving its ID
            new_hit_id = api.create_hit_with_type(hittypeid, question, lifetime, workers, 'batch%r' % group_id)['HITId']
            logger.info("Creating hit with id %s" % new_hit_id)
            # Using saved ID to update DB-schema
            new_mini_hit.id = new_hit_id
            new_mini_hit.status = 'active'
    db.session.commit()


def check_tracked_hits():
    logger.info('Checking Tracked HITs')
    query = db.session.query(TrackedHIT)\
        .filter(TrackedHIT.active.is_(True)).all()

    for thit in query:
        hit = api.get_hit(thit.id)
        if hit['HITStatus'] != 'Reviewable':
            continue
        logger.info('HIT %s is Reviewable. Updating Database.' % thit.id)
        thit.active = False
        assignments = api.list_assignments_for_hit(thit.id)
        for a in assignments:
            worker = Worker.query.filter(Worker.id == a['WorkerId']).one_or_none()

            if worker is None:
                logger.info('Creating Worker %s.' % a['WorkerId'])
                worker = Worker(id=a['WorkerId'])
                if a['AssignmentStatus'] == 'Approved':
                    worker.no_approved = 1
                elif a['AssignmentStatus'] == 'Rejected':
                    worker.no_rejected = 1
                db.session.add(worker)
            else:
                logger.info('Updating Workers %s total number of participated assignments.' % a['WorkerId'])
                worker.no_assignments += 1
    db.session.commit()


db.create_all()

import os
if os.environ.get('WERKZEUG_RUN_MAIN') is None:  # Make Scheduler be created once, else it will run twice if app is ran in DEBUG-mode which will screw up the database
    scheduler = BackgroundScheduler()
    scheduler.add_job(update_mini_hits, 'interval', seconds=60)
    scheduler.add_job(check_tracked_hits, 'interval', seconds=60)
    scheduler.start()


@app.route('/approve_assignment/<awsid:assignmentid>/<awsid:workerid>', methods=['PATCH'])
def approve_route(assignmentid, workerid):
    logger.info('Approving worker %s from Assignment %s.' % (workerid, assignmentid))
    response = api.approve_assignment(assignmentid)
    if response is None:
        worker = Worker.query.filter(Worker.id == workerid).one_or_none()
        if worker is None:
            # Normally the worker will be created once a HIT is finished (in update_mini_hits)
            # If the results are approved while the HIT is still assignable we have to create the worker now.
            worker = Worker(id=workerid, no_assignments=0, no_approved=1)
            db.session.add(worker)
        else:
            worker.no_approved += 1
        db.session.commit()
        return jsonify({'success': True}), 200
    else:
        return jsonify({'success': False, 'error': response}), 423


@app.route('/reject_assignment/<awsid:assignmentid>/<awsid:workerid>', methods=['PATCH'])
def reject_route(assignmentid, workerid):
    logger.info('Rejecting worker %s from Assignment %s.' % (workerid, assignmentid))
    response = api.reject_assignment(assignmentid, app.config.get('DEFAULT_REJECTION_MESSAGE'))
    if response is None:
        worker = Worker.query.filter(Worker.id == workerid).one_or_none()
        if worker is None:
            # Normally the worker will be created once a HIT is finished (in update_mini_hits)
            # If the results are approved while the HIT is still assignable we have to create the worker now.
            worker = Worker(id=workerid, no_assignments=0, no_rejected=1)
            db.session.add(worker)
        else:
            worker.no_rejected += 1
        db.session.commit()
        return jsonify({'success': True}), 200
    else:
        return jsonify({'success': False, 'error': response}), 423


@app.route('/delete_hit/<awsid:hitid>', methods=['DELETE'])
def delete_route(hitid):
    logger.info('Deleting HIT %s.' % hitid)
    resp = api.delete_hit(hitid)
    if resp['success']:
        tracked_hit = TrackedHIT.query.filter(TrackedHIT.id == hitid).one_or_none()
        if tracked_hit:
            db.session.delete(tracked_hit)
            db.session.commit()
    return jsonify(resp)


######################################################################
#                          DEBUGGING ROUTES                          #
######################################################################


@app.route('/approve_all/<awsid:hitid>', methods=['PATCH'])
def approve_all_route(hitid):
    assignments = api.list_assignments_for_hit(hitid)
    errors = []
    for assignment in assignments:
        if(assignment['AssignmentStatus'] == 'Submitted'):
            error = api.approve_assignment(assignment['AssignmentId'])
            if(error is not None):
                errors.append(error)
    if(not errors):
        return jsonify({'success': True}), 200
    else:
        return jsonify({'success': False, 'error': errors}), 423


import time
@app.route('/testingstuff')
def testing_route():
    time.sleep(0.5)
    return jsonify({'success': True})


@app.route('/expire_hit/<awsid:hitid>')
def expire_route(hitid):
    return jsonify(api.expire_hit(hitid))


@app.route('/get_hit/<awsid:hitid>')
def get_route(hitid):
    return jsonify(api.get_hit(hitid))


@app.route("/createsoftblock")
def softblock():
    qualification = api.create_qualification_type("Thank you!", "thanks", "For you splendid performance we award you this special qualification. Thank you again!")
    return jsonify(qualification)


@app.route("/cleardb/<secretkey>")
def cleardb(secretkey):
    if secretkey != app.config.get('SECRET_KEY'):
        return "403 Forbidden"
    db.drop_all()
    db.create_all()
    return "200 OK"


@app.route('/clear_all/<secretkey>')
def clear_all(secretkey, hits=None):
    if secretkey != app.config.get('SECRET_KEY'):
        return "403 Forbidden"
    hits = api.list_all_hits()
    for hit in hits:
        try:
            api.forcedelete_hit(hit['HITId'])
        except api.client.exceptions.ClientError:
            pass
    db.drop_all()
    db.create_all()
    return jsonify(api.list_all_hits())


def delete_hits(hits):
    # we pray that all assignments were approved or rejected already
    # else we got a problem
    for hit in hits:
        id = hit['HITId']
        pending = hit['NumberOfAssignmentsPending']
        if hit['HITStatus'] == 'Reviewable' and pending == 0:
            api.delete_hit(id)
            hits.remove(hit)
        elif hit['HITStatus'] == 'Assignable' and pending == 0:
            # no pending and Assignable => expire and try later
            api.expire_hit(id)
        elif hit['HITStatus'] == 'Unassignable':
            # pending assignments, cant do anything about that
            hits.remove(hit)
    return hits
