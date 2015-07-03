from Acquisition import aq_inner
from zope.interface import alsoProvides
from z3c.form.interfaces import IFormLayer
from plone.z3cform.interfaces import IWrappedForm
from plone.z3cform import z2
from Products.CMFCore.utils import getToolByName
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile

from zope.interface import implements
from zope import schema

from z3c.form import field
from z3c.form.browser.checkbox import CheckBoxFieldWidget

from plone.memoize.compress import xhtml_compress
from plone.memoize.instance import memoize

from plone.portlets.interfaces import IPortletDataProvider

from plone.app.portlets import PloneMessageFactory as _
from plone.app.portlets.portlets import base

from collective.mailchimp.browser.z3cformhelpers import AddForm
from collective.mailchimp.browser.z3cformhelpers import EditForm

from collective.mailchimp.interfaces import INewsletterSubscribe
from collective.mailchimp.browser.newsletter import NewsletterSubscriberForm


class IExtendedMailChimp(IPortletDataProvider):

    name = schema.TextLine(
        title=_(u'Title'),
        description=_(u'Title of the portlet'))

    description = schema.TextLine(
        title=_(u'Description'),
        description=_(u'Description of the portlet'))

    available_lists = schema.List(
        title=_(u'Available lists'),
        description=_(u'Select available lists to subscribe to.'),
        required=True,
        min_length=1,
        value_type=schema.Choice(
            source='collective.mailchimp.vocabularies.AvailableLists'
            )
        )


class Assignment(base.Assignment):
    implements(IExtendedMailChimp)

    def __init__(self, name=u'', description=u'', available_lists=[]):
        self.name = name
        self.description = description
        self.available_lists = available_lists

    @property
    def title(self):
        return _(u"MailChimp")


class Renderer(base.Renderer):
    fields = field.Fields(INewsletterSubscribe)
    _template = ViewPageTemplateFile('alternative_templates/portlet.pt')
    form = NewsletterSubscriberForm

    def __init__(self, *args):
        base.Renderer.__init__(self, *args)

    def render(self):
        return xhtml_compress(self._template())

    @property
    def name(self):
        return self.data.name or _(u"Subscribe to newsletter")

    @property
    def description(self):
        return self.data.description or _(u"")

    @memoize
    def _data(self):
        catalog = getToolByName(self.context, 'portal_catalog')
        return catalog(portal_type='MailChimp Item')

    def update(self):
        super(Renderer, self).update()
        z2.switch_on(self, request_layer=IFormLayer)
        self.form = self.form(aq_inner(self.context), self.request)
        alsoProvides(self.form, IWrappedForm)
        self.form.update()


class AddForm(AddForm):
    fields = field.Fields(IExtendedMailChimp)
    fields['available_lists'].widgetFactory = CheckBoxFieldWidget
    label = _(u"Add MailChimp Portlet")
    description = _(
        u"This portlet displays a subscription form for a " +
        u"MailChimp newsletter.")

    def create(self, data):
        return Assignment(
            name=data.get('name', u''),
            description=data.get('description', u''),
            available_lists=data.get('available_lists', []))


class EditForm(EditForm):
    fields = field.Fields(IExtendedMailChimp)
    fields['available_lists'].widgetFactory = CheckBoxFieldWidget
    label = _(u"Edit MailChimp Portlet")
    description = _(
        u"This portlet displays a subscription form for a " +
        u"MailChimp newsletter.")

