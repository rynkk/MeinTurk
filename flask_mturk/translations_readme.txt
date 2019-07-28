HOW TO CREATE YOUR OWN TRANSLATION



1. create pot:
	
	>pybabel extract -F babel.cfg -k lazy_gettext -o messages.pot .

2. create your ISP 639-1 translationfile: (https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes)

	>pybabel init -i messages.pot -d translations -l "yourlanguageISO_639-1-letters" (eg. de/en/es/fr/..)

3. fill created translationfile with translation:

	>hint: https://translate.google.com/toolkit/list#translations/active

4. compile the file(s):
	
	>pybabel compile -d translations

5. add your language to the babel.route in routes.py

6. add your language to each custom js file

7. add your language to the each main/*.html file (at the bottom)