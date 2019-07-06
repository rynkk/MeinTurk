from flask_wtf import FlaskForm
from flask_wtf.file import FileRequired, FileAllowed
from wtforms import FormField, StringField, BooleanField, DecimalField, RadioField, TextAreaField
from wtforms import SelectField, IntegerField, DateTimeField, SubmitField, FieldList, FileField
from flask_ckeditor import CKEditorField
from wtforms.validators import Optional, InputRequired, DataRequired, Length, ValidationError, Regexp

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
    int_field = IntegerField(default=3, validators=[InputRequired()])
    unit_field = SelectField(default='days', validators=[InputRequired()],
                             choices=[('minutes', 'Minuten'), ('hours', 'Stunden'), ('days', 'Tage')])

    def __init__(self, *args, **kwargs):  # disable CSRF because its a child-Form
        kwargs['csrf_enabled'] = False
        super(IntUnitForm, self).__init__(*args, **kwargs)


class QualificationsSubForm(FlaskForm):
    selector = SelectField()
    first_select = NonValidatingSelectField()
    second_select = NonValidatingSelectField(validators=[Regexp(r'^[\w]+$', message="Qualifications 3rd Select Value invalid")])

    def __init__(self, *args, **kwargs):  # disable CSRF because its a child-Form
        kwargs['csrf_enabled'] = False
        super(QualificationsSubForm, self).__init__(*args, **kwargs)

    def validate_first_select(form, field):  # only allow Exists, DoesNotExist , GreaterThan GreaterThanOrEqualTo LessThan LessThanOrEqualTo EqualTo NotEqualTo In NotIn
        if(field.data not in ["Exists", "DoesNotExist ", "GreaterThan", "GreaterThanOrEqualTo", "LessThan", "LessThanOrEqualTo", "EqualTo", "NotEqualTo", "In", "NotIn"]):
            raise ValidationError("Unable to validate the Qualification-Comparator called:" + '"' + field.data + '"')


class QualificationsForm(FlaskForm):
    selects = FieldList(FormField(QualificationsSubForm))

    def __init__(self, *args, **kwargs):  # disable CSRF because its a child-Form
        kwargs['csrf_enabled'] = False
        super(QualificationsForm, self).__init__(*args, **kwargs)


class SurveyForm(FlaskForm):
    # Allgemein #
    project_name = StringField('Projektname', description='Name des Projekts (Nicht für Bearbeiter einsehbar)', validators=[InputRequired()])
    title = StringField('Titel', description='Titel der Survey der dem Bearbeiter angezeigt wird', validators=[InputRequired()])
    description = StringField('Beschreibung', description='Aussagekräftige Beschreibung der Survey', validators=[InputRequired()])
    keywords = StringField('Schlagwörter', description='Tags, nach denen der Bearbeiter und der Ersteller filtern kann (optional)', validators=[Optional()])
    # starting_date = DateTimeField('Startdatum (GMT+1)', description='Verzögerter Surveybeginn (optional)', validators=[Optional()])
    # starting_date_set = BooleanField('Survey ohne Verzögerung starten', default=True)
    time_till_expiration = FormField(IntUnitForm, 'Dauer bis Ablauf', description='Zeit bis die Survey ungültig und abgebrochen wird (optional)')

    # Worker allgemein #
    amount_workers = IntegerField('Anzahl Bearbeiter', default=20, validators=[InputRequired()])
    minibatch = BooleanField('MiniBatching', description='Durch MiniBatching wird die Survey in mehrere Kleinsurveys a 9 Bearbeiter gegliedert.')
    qualification_name = StringField('MiniBatching-Qualifikationsname', validators=[Optional()],
                                     description='Gibt an, unter welchem Namen die Qualifikation gespeichert wird, die verhindert, dass Worker an mehreren Mini-HITs des gleiches Batches teilnehmen können.')
    payment_per_worker = DecimalField('Bezahlung pro Bearbeiter', description='Summe in Dollar($) die dem Bearbeiter nach erfolgreichem Abschluss ausgezahlt wird', default=0.50, validators=[InputRequired()])
    allotted_time_per_worker = FormField(IntUnitForm, 'Maximale Bearbeitungszeit')
    accept_pay_worker_after = FormField(IntUnitForm, 'Bearbeiter automatisch annehmen und bezahlen nach', description='Titel der für den Bearbeiter angezeigt wird')

    # Worker speziell #
    must_be_master = RadioField('Bearbeiter müssen Master sein', description='Master sind Bearbeiter mit herausragender Bearbeitungsqualität', choices=[('yes', 'Ja'), ('no', 'Nein')],
                                default='no', validators=[InputRequired()])
    qualifications_select = FormField(QualificationsForm, 'Lege alle zusätzlichen Qualifikationen fest', description='Legt Qualifikationen fest, die ein Bearbeiter vorweisen muss, um diese Survey bearbeiten zu dürfen')
    adult_content = BooleanField('Projekt enthält nicht jugendfreie Inhalte', default=False,
                                 validators=[Optional()])
    project_visibility = RadioField('Sichtbarkeit', description='Sichtbar: Man kann die Survey ohne Qualifikation nicht annehmen; Privat: Weder annehmen noch Vorschau ansehen; Versteckt: Weder annehmen, noch Vorschau, noch überhaupt Sehen', default='Accept', validators=[InputRequired()],
                                    choices=[('Accept', 'Öffentlich'), ('PreviewAndAccept ', 'Privat'), ('DiscoverPreviewAndAccept ', 'Versteckt')])

    # SurveyLayout #

    editor_field = CKEditorField('editor_field', default=default_value)

    # Finish #
    submitform = SubmitField('Survey erstellen')

    pages = ['Allgemein', 'Worker allg.', 'Worker speziell', 'SurveyLayout', 'Finish']

    def validate_minibatch(form, field):
        if field.data and form.amount_workers.data < 10:
            raise ValidationError("Stop trying to trick the validation! You can only minibatch with more that 9 workers!")


class UploadForm(FlaskForm):
    file = FileField('file', validators=[
        FileRequired(),
        FileAllowed(['csv', 'xlsx', 'txt', 'someothercsvtypes'], 'Only CSV-Files are allowed!')
    ])
