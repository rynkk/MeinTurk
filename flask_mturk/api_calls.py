import time
from datetime import datetime
import logging

from flask import jsonify
from flask_mturk import client, app
from botocore.exceptions import ClientError

logger = logging.getLogger('apiCalls')


class Api:
    def __init__(self, c):
        self.client = c

    # ## ### Elementary functions ### ## #

    def get_hit(self, hitid):
        try:
            return self.client.get_hit(HITId=hitid)['HIT']
        except ClientError:
            logger.exception('An Error occured trying to get the HIT %s' % hitid)

    def expire_hit(self, hit_id):
        try:
            return self.client.update_expiration_for_hit(HITId=hit_id, ExpireAt=datetime(2015, 1, 1))
        except ClientError:
            logger.exception('An Error occured trying to expire HIT %s' % hit_id)

    def get_balance(self):
        try:
            return self.client.get_account_balance()['AvailableBalance']
        except ClientError:
            logger.exception('An Error occured trying to get the balance')

    def disassociate_qualification_from_worker(self, workerid, qualificationid):
        return self.client.disassociate_qualification_from_worker(
            WorkerId=workerid,
            QualificationTypeId=qualificationid
        )

    def get_qualification_type(self, qualificationid):
        try:
            self.client.get_qualification_type(QualificationTypeId=qualificationid)
            return None
        except ClientError as ce:
            logger.exception('An Error occured trying to get the qualification %s' % qualificationid)
            return ce.response['Error']['Message']

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
            logger.exception('An Error occured trying to delete the HIT %s' % hit_id)
            return {'success': False, 'error': ce.response['Error']['Message']}

    def approve_assignment(self, assignment_id):
        try:
            client.approve_assignment(AssignmentId=assignment_id)
            return None
        except ClientError as ce:
            logger.exception('An Error occured trying to approve the Assignment %s' % assignment_id)
            return ce.response['Error']['Message']

    def reject_assignment(self, assignment_id, reason):
        try:
            client.reject_assignment(AssignmentId=assignment_id, RequesterFeedback=reason)
            return None
        except ClientError as ce:
            logger.exception('An Error occured trying to reject the Assignment %s' % assignment_id)
            return ce.response['Error']['Message']

    def delete_qualification_type(self, qualification_id):
        if(qualification_id != app.config.get('SOFTBLOCK_QUALIFICATION_ID')):
            try:
                return client.delete_qualification_type(QualificationTypeId=qualification_id)
            except ClientError:
                logger.exception('An error occured trying to delete the qualification %s' % qualification_id)
        else:
            logger.critical('Tried to delete the softblock-qualification')
            raise ValueError('Tried to delete Softblock-Qualification')

    def associate_qualification_with_worker(self, worker_id, qualification_id, val=1):
        try:
            client.associate_qualification_with_worker(
                QualificationTypeId=qualification_id,
                WorkerId=worker_id,
                IntegerValue=val,
                SendNotification=False,
            )
            return None
        except ClientError as ce:
            logger.exception('An error occured trying to associate the qualification %s to the worker' % (qualification_id, worker_id))
            return ce.response['Error']['Message']

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
            logger.exception('An error occured trying to send a bonus to the worker %s' % worker_id)
            return ce.response['Error']['Message']

    def create_hit(self, max, autoacc, lifetime, duration, reward, title, keywords, desc, question, qualreq):
        try:
            return self.client.create_hit(
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
        except ClientError:
            logger.exception('An error occured trying to create a HIT')

    def create_hit_with_type(self, hittypeid, question, lifetime, max, reqanno=""):
        try:
            return self.client.create_hit_with_hit_type(
                HITTypeId=hittypeid,
                MaxAssignments=max,
                LifetimeInSeconds=lifetime,
                Question=question,
                RequesterAnnotation=reqanno
            )['HIT']
        except ClientError:
            logger.exception('An error occured trying to create a HIT with Type %s' % hittypeid)

    def create_hit_type(self, autoapp, duration, reward, title, keywords, desc, qualreq):
        try:
            return self.client.create_hit_type(
                AutoApprovalDelayInSeconds=autoapp,
                AssignmentDurationInSeconds=duration,
                Reward=reward,
                Title=title,
                Keywords=keywords,
                Description=desc,
                QualificationRequirements=qualreq
            )['HITTypeId']
        except ClientError:
            logger.exception('An error occured trying to create a HITType')

    def create_qualification_type(self, name, keywords, description, autogrant=False, autograntvalue=None):
        try:
            if not autogrant:
                return client.create_qualification_type(
                    Name=name,
                    Keywords=keywords,
                    Description=description,
                    QualificationTypeStatus='Active',
                )['QualificationType']
            else:
                return client.create_qualification_type(
                    Name=name,
                    Keywords=keywords,
                    Description=description,
                    QualificationTypeStatus='Active',
                    AutoGranted=autogrant,
                    AutoGrantedValue=autograntvalue
                )['QualificationType']
        except ClientError:
            logger.exception('An error occured trying to create a qualification')

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


@app.route('/api/softblock/<awsid:workerid>', methods=['PATCH'])
def softblock_route(workerid):
    response = api.associate_qualification_with_worker(workerid, app.config.get('SOFTBLOCK_QUALIFICATION_ID'))
    if response is None:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': response})


@app.route('/api/assign_qualification/<awsid:workerid>/<awsid:qualificationid>/<int:val>', methods=['PATCH'])
def assign_route(workerid, qualificationid, val):
    error = api.associate_qualification_with_worker(workerid, qualificationid, val)
    if error is None:
        return jsonify({'success': True}), 200
    else:
        return jsonify({'success': False, 'error': error}), 400
