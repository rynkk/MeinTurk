from flask_wtf import FlaskForm
from flask_wtf.file import FileRequired, FileAllowed
from flask_ckeditor import CKEditorField
from flask_babel import lazy_gettext
from wtforms import FormField, StringField, BooleanField, DecimalField, RadioField
from wtforms import SelectField, IntegerField, SubmitField, FieldList, FileField
from wtforms.validators import Optional, InputRequired, ValidationError, Regexp
from wtforms.widgets import HiddenInput
from wtforms.widgets.html5 import NumberInput

default_value = """<!-- For help on using this template, see the blog post: https://blog.mturk.com/editing-the-survey-link-project-template-in-the-ui-7c75285105fb#.py7towsdx --><!-- HIT template: SurveyLink-v3.0 --><!-- The following snippet enables the 'responsive' behavior on smaller screens -->
<meta content="width=device-width,initial-scale=1" name="viewport" />
<section class="container" id="SurveyLink"><!-- Instructions -->
<div class="row">
<div class="col-xs-12 col-md-12">
<div class="panel panel-primary"><!-- WARNING: the ids "collapseTrigger" and "instructionBody" are being used to enable expand/collapse feature --><a class="panel-heading" href="javascript:void(0);" id="collapseTrigger"><strong>Survey Link Instructions</strong> <span class="collapse-text">(Click to expand)</span> </a>
<div class="panel-body" id="instructionBody">
<p>We are conducting an academic survey about social networks. We need to understand your opinion about social networks. Select the link below to complete the survey. At the end of the survey, you will receive a code to paste into the box below to receive credit for taking our survey.</p>

<p><strong>Make sure to leave this window open as you complete the survey. </strong> When you are finished, you will return to this page to paste the code into the box.</p>

<p class="well well-sm"><strong><mark>Template note for Requesters</mark></strong> - To verify that Workers actually complete your survey, require each Worker to enter a <strong>unique</strong> survey completion code to your HIT. Consult with your survey service provider on how to generate this code at the end of your survey.</p>
</div>
</div>
</div>
</div>
<!-- End Instructions --><!-- Survey Link Layout -->

<div class="row" id="workContent">
<div class="col-xs-12 col-md-6 col-md-offset-3"><!-- Content for Worker -->
<table class="table table-condensed table-bordered">
<colgroup>
<col class="col-xs-4 col-md-4" />
<col class="col-xs-8 col-md-8" />
</colgroup>
<tbody>
<tr>
<td><label>Survey link:</label></td>
<td><a class="dont-break-out" href="http://[example.com/survey345.html]" target="_blank">http://example.com/survey345.html</a></td>
</tr>
</tbody>
</table>
<!-- End Content for Worker --><!-- Input from Worker -->

<div class="form-group"><label for="surveycode">Provide the survey code here:</label> <input class="form-control" id="surveycode" name="surveycode" placeholder="e.g. 123456" required="" type="text" /></div>
<!-- End input from Worker --></div>
</div>
<!-- End Survey Link Layout --></section>
<!-- Please note that Bootstrap CSS/JS and JQuery are 3rd party libraries that may update their url/code at any time. Amazon Mechanical Turk (MTurk) is including these libraries as a default option for you, but is not responsible for any changes to the external libraries --><!-- External CSS references -->
<link crossorigin="anonymous" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.0.3/css/bootstrap.min.css" integrity="sha384-IS73LIqjtYesmURkDE9MXKbXqYA8rvKEp/ghicjem7Vc3mGRdQRptJSz60tvrB6+" rel="stylesheet" /><!-- Open internal style sheet -->
<style type="text/css">#collapseTrigger{
  color:#fff;
  display: block;
  text-decoration: none;
}
#submitButton{
  white-space: normal;
}
.image{
  margin-bottom: 15px;
}
/* CSS for breaking long words/urls */
.dont-break-out {
  overflow-wrap: break-word;
  word-wrap: break-word;
  -ms-word-break: break-all;
  word-break: break-all;
  word-break: break-word;
  -ms-hyphens: auto;
  -moz-hyphens: auto;
  -webkit-hyphens: auto;
  hyphens: auto;
}
</style>
<!-- Close internal style sheet --><!-- External JS references --><script src="https://code.jquery.com/jquery-3.1.0.min.js"   integrity="sha256-cCueBR6CsyA4/9szpPfrX3s49M9vUU5BgtiJj06wt/s="   crossorigin="anonymous"></script><script src="https://maxcdn.bootstrapcdn.com/bootstrap/3.0.3/js/bootstrap.min.js" integrity="sha384-s1ITto93iSMDxlp/79qhWHi+LsIi9Gx6yL+cOKDuymvihkfol83TYbLbOw+W/wv4" crossorigin="anonymous"></script><!-- Open internal javascript --><script>
  $(document).ready(function() {
    // Instructions expand/collapse
    var content = $('#instructionBody');
    var trigger = $('#collapseTrigger');
    content.hide();
    $('.collapse-text').text('(Click to expand)');
    trigger.click(function(){
      content.toggle();
      var isVisible = content.is(':visible');
      if(isVisible){
        $('.collapse-text').text('(Click to collapse)');
      }else{
        $('.collapse-text').text('(Click to expand)');
      }
    });
    // end expand/collapse
  });
</script><!-- Close internal javascript -->"""


class NonValidatingSelectField(SelectField):
    def pre_validate(self, form):  # Disable choices-check
        pass


class IntUnitForm(FlaskForm):
    int_field = IntegerField(default=1, validators=[InputRequired()], widget=NumberInput(min=1))  # 1 minutes for testing
    unit_field = SelectField(default='minutes', validators=[InputRequired()],
                             choices=[('minutes', lazy_gettext('Minutes')), ('hours', lazy_gettext('Hours')), ('days', lazy_gettext('Days'))])

    def __init__(self, *args, **kwargs):  # disable CSRF because its a child-Form
        kwargs['csrf_enabled'] = False
        super(IntUnitForm, self).__init__(*args, **kwargs)


class QualificationsSubForm(FlaskForm):
    selector = SelectField()
    first_select = NonValidatingSelectField()
    second_select = NonValidatingSelectField(validators=[Regexp(r'^[\w]+$', message=lazy_gettext("Qualifications 3rd Select Value invalid"))])

    def __init__(self, *args, **kwargs):  # disable CSRF because its a child-Form
        kwargs['csrf_enabled'] = False
        super(QualificationsSubForm, self).__init__(*args, **kwargs)

    def validate_first_select(form, field):  # only allow Exists, DoesNotExist , GreaterThan GreaterThanOrEqualTo LessThan LessThanOrEqualTo EqualTo NotEqualTo In NotIn
        if(field.data not in ["Exists", "DoesNotExist", "GreaterThan", "GreaterThanOrEqualTo", "LessThan", "LessThanOrEqualTo", "EqualTo", "NotEqualTo", "In", "NotIn"]):
            raise ValidationError(lazy_gettext('Unable to validate the Qualification-Comparator called: "%s"') % field.data)


class QualificationsForm(FlaskForm):
    selects = FieldList(FormField(QualificationsSubForm))

    def __init__(self, *args, **kwargs):  # disable CSRF because its a child-Form
        kwargs['csrf_enabled'] = False
        super(QualificationsForm, self).__init__(*args, **kwargs)


class SurveyForm(FlaskForm):
    # Allgemein #
    project_name = StringField(lazy_gettext('Project name'), description=lazy_gettext('Name of the project. (Not visible to workers)'), validators=[InputRequired()])
    title = StringField(lazy_gettext('Title'), description=lazy_gettext('Survey title being displayed to workers.'), validators=[InputRequired()])
    description = StringField(lazy_gettext('Description'), description=lazy_gettext('Comprehensive description of your survey.'), validators=[InputRequired()])
    keywords = StringField(lazy_gettext('Keywords'), description=lazy_gettext('Keywords which either you or the workers can search for. (optional)'), validators=[Optional()])
    time_till_expiration = FormField(IntUnitForm, lazy_gettext('Time till expiration'), description=lazy_gettext('Time until the survey expires and becomes unavailable to workers. MINIBATCHING: This will be assigned to each MiniHIT of the batch!'))

    # Worker allgemein #
    amount_workers = IntegerField(lazy_gettext('Amount workers'), description=lazy_gettext('The amount of workers that can work on your survey. MINIBATCHING: MiniHIT will automatically be generated to reach this amount of submissions!'), default=20, validators=[InputRequired()], widget=NumberInput(min=1))
    minibatch = BooleanField(lazy_gettext('MiniBatching'), description=lazy_gettext('MiniBatching will divide your survey into multiple smaller surveys with max. 9 workers each to save fees.'))
    qualification_name = StringField(lazy_gettext('MiniBatching-Qualification name'), validators=[Optional()],
                                     description=lazy_gettext('This will be the name under which the qualification for this batch will be saved. This qualification will prevent multiple submissions from the same worker within this batch.'))
    payment_per_worker = DecimalField('Payment per worker', description='Sum of Dollars($) that will be paid to workers on approval.', default=0.50, validators=[InputRequired()], widget=NumberInput(min=0.00, max=10, step=0.01))
    allotted_time_per_worker = FormField(IntUnitForm, lazy_gettext('Allotted time'), description=lazy_gettext('Amount of time each worker has to submit his results.'))
    accept_pay_worker_after = FormField(IntUnitForm, lazy_gettext('Pay and accept worker after'), description=lazy_gettext('Amount of time until submissions are auto-approved and paid.'))

    # Worker speziell #
    must_be_master = RadioField(lazy_gettext('Workers must be Master'), description=lazy_gettext('Master are workers with disinguished submission-quality. This will create additional fees.'), choices=[('yes', lazy_gettext('Yes')), ('no', lazy_gettext('No'))],
                                default='no', validators=[InputRequired()])
    qualifications_select = FormField(QualificationsForm, lazy_gettext('Choose all necessary qualifications for this survey.'), description=lazy_gettext('Workers that do not have the chosen qualifications will be unable to participate in the survey.'))
    adult_content = BooleanField(lazy_gettext('Project contains adult content'), description=lazy_gettext('Workers unwilling or not allowed to see adult content will be excluded from the survey if this is checked.'), default=False,
                                 validators=[Optional()])
    project_visibility = RadioField(lazy_gettext('Visibility'), description=lazy_gettext('Public: Cannot accept the Survey without the right qualifications.; Private: Cannot accept nor preview without the right qualifications.; Hidden: Cannot accept, preview nor see the survey without the right qualifications.'), default='Accept', validators=[InputRequired()],
                                    choices=[('Accept', lazy_gettext('Public')), ('PreviewAndAccept ', lazy_gettext('Private')), ('DiscoverPreviewAndAccept ', lazy_gettext('Hidden'))])

    # SurveyLayout #

    editor_field = CKEditorField('editor_field', default=default_value)

    # Finish #
    submitform = SubmitField(lazy_gettext('Create Survey'))

    pages = [lazy_gettext('General'), lazy_gettext('Worker'), lazy_gettext('Qualifications'), lazy_gettext('Layout'), lazy_gettext('Finish')]

    def validate_minibatch(form, field):
        if field.data and form.amount_workers.data < 10:
            raise ValidationError(lazy_gettext("Stop trying to trick the validation! You can only minibatch with more that 9 workers!"))


class UploadForm(FlaskForm):
    hit_batched = BooleanField(validators=[InputRequired(lazy_gettext('Could not set if HIT batched or not!'))], widget=HiddenInput())
    hit_identifier = StringField(validators=[InputRequired(lazy_gettext('Could not set HIT-Id!'))], widget=HiddenInput())
    file = FileField('file', validators=[
        FileRequired(),
        FileAllowed(['csv', 'xlsx', 'txt'], lazy_gettext('Only CSV-Files are allowed!'))
    ])


class QualificationCreationForm(FlaskForm):
    name = StringField(lazy_gettext('Name'), validators=[InputRequired(lazy_gettext('Please enter a name!'))])
    desc = StringField(lazy_gettext('Description'), validators=[InputRequired(lazy_gettext('Please enter a description!'))])
    keywords = StringField(lazy_gettext('Keywords'), validators=[Optional()])
    auto_granted = BooleanField(lazy_gettext('AutoGranted'), description=lazy_gettext('AutoGranted qualifications are automatically assigned to workers who work on a HIT containing that AutoGranted qualification.'), validators=[Optional()])
    auto_granted_value = IntegerField(lazy_gettext('AutoGranted Value'), validators=[Optional()], default=1, widget=NumberInput(min=0, max=100, step=1))
