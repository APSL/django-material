from django.contrib.auth import get_permission_codename
from django.core.urlresolvers import reverse
from django.core.exceptions import PermissionDenied, ImproperlyConfigured
from django.db import models
from django.views import generic
from django.forms import models as model_forms


class DetailModelView(generic.DetailView):
    """Thin wrapper for `generic.DetailView`."""

    viewset = None
    form_class = None
    layout = None
    fields = None

    def __init__(self, *args, **kwargs):  # noqa D102
        super(DetailModelView, self).__init__(*args, **kwargs)
        if self.form_class is None and self.fields is None:
            self.fields = '__all__'

    def get_object_data(self):
        """List of object fields to display.

        Choice fields values are expanded to readable choice label.
        """
        for field in self.object._meta.fields:
            if isinstance(field, models.AutoField):
                continue
            elif field.auto_created:
                continue
            else:
                choice_display_attr = "get_{}_display".format(field.get_attname())
            if hasattr(self.object, choice_display_attr):
                value = getattr(self.object, choice_display_attr)()
            else:
                value = getattr(self.object, field.get_attname())

                if value is not None:
                    yield (field.verbose_name.title(), value)

    def has_view_permission(self, request, obj):
        """Object view permission check.

        If view had a `viewset`, the `viewset.has_view_permission` used.
        """
        if self.viewset is not None:
            return self.viewset.has_view_permission(request, obj)

        # default lookup for the django permission
        opts = self.model._meta
        codename = get_permission_codename('view', opts)
        view_perm = '{}.{}'.format(opts.app_label, codename)
        if request.user.has_perm(view_perm, obj=obj):
            return True
        return self.has_change_permission(request, obj=obj)

    def has_change_permission(self, request, obj):
        """Object chane permission check.

        If view had a `viewset`, the `viewset.has_change_permission` used.

        If true, view will show `Change` link to the Change view.
        """
        if self.viewset is not None:
            return self.viewset.has_change_permission(request, obj)

        # default lookup for the django permission
        opts = self.model._meta
        codename = get_permission_codename('change', opts)
        return request.user.has_perm(
            '{}.{}'.format(opts.app_label, codename), obj=obj)

    def has_delete_permission(self, request, obj):
        """Object delete permission check.

        If true, view will show `Delete` link to the Delete view.
        """
        if self.viewset is not None:
            return self.viewset.has_delete_permission(request, obj)

        # default lookup for the django permission
        opts = self.model._meta
        codename = get_permission_codename('delete', opts)
        return request.user.has_perm(
            '{}.{}'.format(opts.app_label, codename), obj=obj)

    def get_object(self):
        """Retrieve the object.

        Check object view permission at the same time.
        """
        obj = super(DetailModelView, self).get_object()
        if not self.has_view_permission(self.request, obj):
            raise PermissionDenied
        return obj

    def get_form_class(self):
        """
        Returns the form class to use in this view.
        """
        if self.fields is not None and self.form_class:
            raise ImproperlyConfigured(
                "Specifying both 'fields' and 'form_class' is not permitted."
            )
        if self.form_class:
            return self.form_class
        else:
            if self.model is not None:
                # If a model has been explicitly provided, use it
                model = self.model
            elif hasattr(self, 'object') and self.object is not None:
                # If this view is operating on a single object, use
                # the class of that object
                model = self.object.__class__
            else:
                # Try to get a queryset and extract the model class
                # from that
                model = self.get_queryset().model

            if self.fields is None:
                raise ImproperlyConfigured(
                    "Using ModelFormMixin (base class of %s) without "
                    "the 'fields' attribute is prohibited." % self.__class__.__name__
                )

            return model_forms.modelform_factory(model, fields=self.fields)

    def get_context_data(self, **kwargs):
        """Additional context data for detail view.

        :keyword object_data: List of fields and values of the object
        :keyword change_url: Link to the change view
        :keyword delete_url: Link to the delete view
        """
        opts = self.model._meta

        kwargs['object_data'] = self.get_object_data()
        if self.has_change_permission(self.request, self.object):
            kwargs['change_url'] = reverse(
                '{}:{}_change'.format(opts.app_label, opts.model_name),
                args=[self.object.pk])
        if self.has_delete_permission(self.request, self.object):
            kwargs['delete_url'] = reverse(
                '{}:{}_delete'.format(opts.app_label, opts.model_name),
                args=[self.object.pk])
        kwargs['form'] = self.get_form_class()(instance=self.object)
        return super(DetailModelView, self).get_context_data(**kwargs)

    def get_template_names(self):
        """
        List of templates for the view.

        If no `self.template_name` defined, returns::

             [<app_label>/<model_label>_detail.html
              'material/frontend/views/detail.html']
        """
        if self.template_name is None:
            opts = self.model._meta
            return [
                '{}/{}{}.html'.format(
                    opts.app_label,
                    opts.model_name,
                    self.template_name_suffix),
                'material/frontend/views/detail.html',
            ]

        return [self.template_name]
