from flask_wtf import FlaskForm
from wtforms import FormField, StringField, BooleanField, DecimalField, RadioField, TextAreaField
from wtforms import SelectField, IntegerField, DateTimeField, SubmitField, FieldList  # SelectMultipleField
# from wtforms.fields.html5 import DecimalRangeField
from flask_ckeditor import CKEditorField
from wtforms.validators import Optional, InputRequired, DataRequired, Length, EqualTo, NumberRange, ValidationError
from flask_mturk.models import User


class NonValidatingSelectField(SelectField):
    def pre_validate(self, form):
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
    second_select = NonValidatingSelectField()

    def __init__(self, *args, **kwargs):  # disable CSRF because its a child-Form
        kwargs['csrf_enabled'] = False
        super(QualificationsSubForm, self).__init__(*args, **kwargs)

    def validate_first_select(form, field):  # only allow Exists, NotExists, GreaterThan GreaterThanOrEqualTo LessThan LessThanOrEqualTo EqualTo NotEqualTo In NotIn
        print(field.data)
        print("TODO - Custom Qualifications Validator First Selects")
        if(field.data not in ["Exists", "NotExists", "GreaterThan", "GreaterThanOrEqualTo", "LessThan", "LessThanOrEqualTo", "EqualTo", "NotEqualTo", "In", "NotIn"]):
            raise ValidationError("You shouldn't manually change the options. Refer to the documentation if you want to add new options.")

    def validate_second_select(form, field):  # Todo: only allow Letters, numbers, spaces (check 3166-format)
        if(field.data):
            print(field.data)
            print("TODO - Custom Qualifications Validator Second Selects")
        # raise ValidationError("You shouldn't manually change the options. Refer to the documentation if you want to add new options.")


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
    starting_date = DateTimeField('Startdatum (GMT+1)', description='Verzögerter Surveybeginn (optional)', validators=[Optional()])
    starting_date_set = BooleanField('Survey ohne Verzögerung starten', default=True)
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
    project_visibility = RadioField('Sichtbarkeit', description='Sichtbar: Jeder kann die Survey sehen; Privat: Nur; Versteckt: Nur', default='public', validators=[InputRequired()],
                                    choices=[('public', 'Öffentlich'), ('private', 'Privat'), ('hidden', 'Versteckt')])

    # SurveyLayout #

    editor_field = CKEditorField('editor_field')

    # Finish #
    submit = SubmitField('Survey erstellen')

    pages = ['Allgemein', 'Worker allg.', 'Worker speziell', 'SurveyLayout', 'Finish']
