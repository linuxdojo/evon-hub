from django.contrib.admin.widgets import FilteredSelectMultiple
from django.forms.widgets import Select
from django.contrib import admin
from django.db import models
from hub.models import *


@admin.register(Server)
@admin.register(ServerGroup)
@admin.register(Policy)
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

