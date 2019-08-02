import time
from datetime import datetime

from flask import jsonify
from flask_mturk import client, app
from botocore.exceptions import ClientError


class Api:
    def __init__(self, c):
        self.client = c

    # ## ### Elementary functions ### ## #

    def get_hit(self, hitid):
        return self.client.get_hit(HITId=hitid)['HIT']

    def expire_hit(self, hit_id):
        return self.client.update_expiration_for_hit(HITId=hit_id, ExpireAt=datetime(2015, 1, 1))

    def get_balance(self):
        return self.client.get_account_balance()['AvailableBalance']

    def disassociate_qualification_from_worker(self, workerid, qualificationid):
        return self.client.disassociate_qualification_from_worker(
            WorkerId=workerid,
            QualificationTypeId=qualificationid
        )

    # not needed for now
    def get_qualification_score(self, workerid, qualificationid):
        return self.client.get_qualification_score(
            QualificationTypeId=qualificationid,
            WorkerId=workerid
        )

    def delete_hit(self, hit_id):
        try:
            return {'success': True, 'data': self.client.delete_hit(HITId=hit_id)}
        except ClientError as ce:
            return {'success': False, 'error': ce.response['Error']['Message']}

    def approve_assignment(self, assignment_id):
        try:
            client.approve_assignment(AssignmentId=assignment_id)
            return None
        except ClientError as ce:
            return ce.response['Error']['Message']

    def reject_assignment(self, assignment_id, reason):
        try:
            client.reject_assignment(AssignmentId=assignment_id, RequesterFeedback=reason)
            return None
        except ClientError as ce:
            return ce.response['Error']['Message']

    def delete_qualification_type(self, qualification_id):
        if(qualification_id != app.config.get('SOFTBLOCK_QUALIFICATION_ID')):
            return client.delete_qualification_type(QualificationTypeId=qualification_id)
        else:
            raise ValueError('Tried to delete Softblock-Qualification')

    def associate_qualification_with_worker(self, worker_id, qualification_id):
        return client.associate_qualification_with_worker(
            QualificationTypeId=qualification_id,
            WorkerId=worker_id,
            IntegerValue=1,
            SendNotification=False,
        )

    def send_bonus(self, worker_id, assignment_id, bonus_amount, reason, token):
        try:
            client.send_bonus(
                WorkerId=worker_id,
                BonusAmount=bonus_amount,
                AssignmentId=assignment_id,
                Reason=reason,
                UniqueRequestToken=token
            )
            return None
        except ClientError as ce:
            return ce.response['Error']['Message']

    def create_hit(self, max, autoacc, lifetime, duration, reward, title, keywords, desc, question, qualreq):
        response = self.client.create_hit(
            MaxAssignments=max,
            AutoApprovalDelayInSeconds=autoacc,
            LifetimeInSeconds=lifetime,
            AssignmentDurationInSeconds=duration,
            Reward=reward,
            Title=title,
            Keywords=keywords,
            Description=desc,
            Question=question,
            QualificationRequirements=qualreq
        )['HIT']
        return response

    def create_hit_with_type(self, hittypeid, question, lifetime, max, reqanno=""):
        response = self.client.create_hit_with_hit_type(
            HITTypeId=hittypeid,
            MaxAssignments=max,
            LifetimeInSeconds=lifetime,
            Question=question,
            RequesterAnnotation=reqanno
        )['HIT']
        return response

    def create_hit_type(self, autoapp, duration, reward, title, keywords, desc, qualreq):
        response = self.client.create_hit_type(
            AutoApprovalDelayInSeconds=autoapp,
            AssignmentDurationInSeconds=duration,
            Reward=reward,
            Title=title,
            Keywords=keywords,
            Description=desc,
            QualificationRequirements=qualreq
        )
        return response['HITTypeId']

    def create_qualification_type(self, name, keywords, description, autogrant=False, autograntvalue=None):
        if not autogrant:
            response = client.create_qualification_type(
                Name=name,
                Keywords=keywords,
                Description=description,
                QualificationTypeStatus='Active',
            )['QualificationType']
        else:
            response = client.create_qualification_type(
                Name=name,
                Keywords=keywords,
                Description=description,
                QualificationTypeStatus='Active',
                AutoGranted=autogrant,
                AutoGrantedValue=autograntvalue
            )['QualificationType']
        return response

    # ## ### Paginated functions ### ## #

    # major bottleneck if more than 100 HITs
    def list_all_hits(self):
        result = []
        paginator = self.client.get_paginator('list_hits')
        pages = paginator.paginate(PaginationConfig={'PageSize': 100})
        for page in pages:
            result += page['HITs']
        return result

    def list_assignments_for_hit(self, hitid, status=None):
        result = []
        if status is None:
            status = ['Submitted', 'Approved', 'Rejected']
        paginator = self.client.get_paginator('list_assignments_for_hit')
        pages = paginator.paginate(
            HITId=hitid,
            AssignmentStatuses=status,
            PaginationConfig={'PageSize': 100}
        )
        for page in pages:
            result += page['Assignments']
        return result

    def list_bonus_payments_for_hit(self, hitid):
        result = []
        paginator = self.client.get_paginator('list_bonus_payments')
        pages = paginator.paginate(
            HITId=hitid,
            PaginationConfig={'PageSize': 100}
        )
        for page in pages:
            result += page['BonusPayments']
        return result

    def list_bonus_payments_for_assignment(self, assignmentid):
        return self.client.list_bonus_payments(AssignmentId=assignmentid)['BonusPayments']

    def list_custom_qualifications(self):
        result = []
        paginator = self.client.get_paginator('list_qualification_types')
        pages = paginator.paginate(
            MustBeRequestable=False,
            MustBeOwnedByCaller=True,
            PaginationConfig={'PageSize': 100}
        )
        for page in pages:
            result += page['QualificationTypes']
        return result

    def list_workers_with_qualification_type(self, qualification_id):
        result = []
        paginator = self.client.get_paginator('list_workers_with_qualification_type')
        pages = paginator.paginate(
            QualificationTypeId=qualification_id,
            PaginationConfig={'PageSize': 100}
        )
        for page in pages:
            result += page['Qualifications']
        return result

    # ## ### Combined functions ### ## #

    def forcedelete_hit(self, hit_id):
        self.expire_hit(hit_id)
        time.sleep(1)
        self.delete_hit(hit_id)

    def delete_hits(self, hit_ids):
        for id in hit_ids:
            self.delete_hit(id)

    def list_bonus_payments_for_hits(self, hit_ids):
        result = []
        for id in hit_ids:
            result += self.list_bonus_payments_for_hit(id)
        return result

    def list_assignments_for_hits(self, hit_ids, status=None):
        result = []
        for id in hit_ids:
            result += self.list_assignments_for_hit(id, status)
        return result

    def grant_qualifications_for_hit(self, hit_id, qualification_id):
        assignments = self.list_assignments_for_hit(hit_id)
        workers = []
        for assignment in assignments:
            self.associate_qualification_with_worker(assignment['WorkerId'], qualification_id)
            workers.append(assignment['WorkerId'])
        return {'success': True, 'workers': workers}


api = Api(client)


@app.route('/api/list_workers_with_qualification_type/<awsid:qualification_id>')
def list_workers_with_qualification_route(qualification_id):
    return jsonify(api.list_workers_with_qualification_type(qualification_id))


@app.route('/api/delete_qualification_type/<awsid:qualification_id>', methods=['DELETE'])
def delete_qualification_route(qualification_id):
    return jsonify(api.delete_qualification_type(qualification_id))


@app.route("/list_payments/<awsid:id>")
def list_payments(id):
    payments = api.list_bonus_payments_for_hit(id)
    return jsonify(payments)


@app.route('/delete_hit/<awsid:id>', methods=['DELETE'])
def delete_hit(id):
    return jsonify(api.delete_hit(id))


@app.route('/api/approve_assignment/<awsid:assignmentid>', methods=['PATCH'])
def approve_route(assignmentid):
    response = api.approve_assignment(assignmentid)
    if response is None:
        return jsonify({'success': True}), 200
    else:
        return jsonify({'success': False, 'error': response}), 423


@app.route('/api/reject_assignment/<awsid:assignmentid>', methods=['PATCH'])
def reject_route(assignmentid):
    response = api.reject_assignment(assignmentid, app.config.get('DEFAULT_REJECTION_MESSAGE'))
    if response is None:
        return jsonify({'success': True}), 200
    else:
        return jsonify({'success': False, 'error': response}), 423


@app.route('/api/approve_all/<awsid:hitid>', methods=['PATCH'])
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
