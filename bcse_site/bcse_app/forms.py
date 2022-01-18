from django import forms
from django.forms import ModelForm
from bcse_app import models


class ReservationForm(ModelForm):
  equipment_types = forms.ModelMultipleChoiceField(required=False,
                                  queryset=models.EquipmentType.objects.all().filter(status='A').order_by('name'))
 
  class Meta:
    model = models.Reservation
    exclude = ('equipment', 'created_by', 'created_date', 'modified_date')
    widgets = {
      'equipment_type': forms.SelectMultiple(attrs={'size':5}),
      #'other_activity': forms.CheckboxInput(),
    }

  def __init__(self, *args, **kwargs):
    super(ReservationForm, self).__init__(*args, **kwargs)

    for field_name, field in list(self.fields.items()):
      if field_name not in ['other_activity', 'need_equipment', 'additional_help', 'need_activity_kit']:
        field.widget.attrs['class'] = 'form-control'
      else:
        field.widget.attrs['class'] = 'form-check-input'
      field.widget.attrs['aria-describedby'] = field.label
      field.widget.attrs['placeholder'] = field.help_text

    if self.instance.id:
      initial = []
      for equipment in self.instance.equipment.all():
        initial.append(equipment.equipment_type.id)
      self.fields['equipment_types'].initial = initial


class WorkshopForm(ModelForm):

  class Meta:
    model = models.Workshop
    exclude = ('created_date', 'modified_date')


  def __init__(self, *args, **kwargs):
    super(WorkshopForm, self).__init__(*args, **kwargs)

    for field_name, field in list(self.fields.items()):
      if field_name not in ['enable_registration']:
        field.widget.attrs['class'] = 'form-control'
      else:
        field.widget.attrs['class'] = 'form-check-input'
      field.widget.attrs['aria-describedby'] = field.label
      field.widget.attrs['placeholder'] = field.help_text

class WorkshopRegistrationSettingForm(ModelForm):

  class Meta:
    model = models.WorkshopRegistrationSetting
    exclude = ('created_date', 'modified_date')


  def __init__(self, *args, **kwargs):
    super(WorkshopRegistrationSettingForm, self).__init__(*args, **kwargs)

    for field_name, field in list(self.fields.items()):
      if field_name not in ['enable_waitlist']:
        field.widget.attrs['class'] = 'form-control'
      else:
        field.widget.attrs['class'] = 'form-check-input'
      field.widget.attrs['aria-describedby'] = field.label
      field.widget.attrs['placeholder'] = field.help_text
