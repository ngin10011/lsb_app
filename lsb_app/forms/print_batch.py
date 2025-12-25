# lsb_app/forms/print_batch.py
from flask_wtf import FlaskForm
from wtforms import BooleanField, HiddenField, FieldList, FormField, DateField, SubmitField
from wtforms.validators import DataRequired

class PrintBatchItemForm(FlaskForm):
    auftrag_id = HiddenField()
    checked = BooleanField()

class PrintBatchToSentForm(FlaskForm):
    versanddatum = DateField("Versanddatum", validators=[DataRequired()])
    items = FieldList(FormField(PrintBatchItemForm), min_entries=0)
    submit = SubmitField("Eintragen")
