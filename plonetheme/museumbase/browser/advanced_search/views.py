#!/usr/bin/python
# -*- coding: utf-8 -*-


from ..views import CommonBrowserView
from plone.app.search.browser import Search
from AccessControl import getSecurityManager
from zope.component import getUtility
from plone.registry.interfaces import IRegistry

class AdvancedSearchView(CommonBrowserView, Search):
    """
    Adding to Search view
    """

    def getItemTitle(self, item):
        title = item.Title()

        if item.portal_type == "Object":
            if item.identification_identification_objectNumber:
                title = "%s - %s" %(item.identification_identification_objectNumber, title)

        return title

    def checkUserPermission(self):
        sm = getSecurityManager()
        if sm.checkPermission(ModifyPortalContent, self.context):
            return True
        return False

    def getAdvancedFields(self):
        searchFilters = []
        registry = getUtility(IRegistry)
        searchFiltersRecord = registry['advancedsearch.fields']
        if searchFiltersRecord:
            filters = list(searchFiltersRecord)
            if filters:
                searchFilters = [advanced_filter for advanced_filter in filters if advanced_filter != ""]

        return searchFilters
