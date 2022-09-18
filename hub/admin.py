from django.contrib import admin
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.db import models
from django.forms.widgets import Select
from solo.admin import SingletonModelAdmin

import hub.models


@admin.register(hub.models.Server)
@admin.register(hub.models.ServerGroup)
@admin.register(hub.models.Policy)
@admin.register(hub.models.Config)
class ModelAdmin(admin.ModelAdmin):
    formfield_overrides = {
        models.ManyToManyField: {'widget': FilteredSelectMultiple("items", False)},
        #models.ForeignKey: {'widget': Select(attrs={"class": "form-control selectpicker", "data-live-search": "true"})},
        models.ForeignKey: {'widget': Select(attrs={"class": "form-control"})},
        }

    class Media:
        #extend = False
        #css = {'all': ('https://cdnjs.cloudflare.com/ajax/libs/bootstrap-select/1.9.4/css/bootstrap-select.min.css',)}
        #js = ('https://cdnjs.cloudflare.com/ajax/libs/bootstrap-select/1.9.4/js/bootstrap-select.min.js',)
        pass
