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

    def checkUserPermission(self):
        sm = getSecurityManager()
        if sm.checkPermission(ModifyPortalContent, self.context):
            return True
        return False

    def getAdvancedFields(self):

        context_url = self.context.absolute_url()

        advanced_widgets = {
            'identification_identification_collection': {
                'data': '{"orderable": true, "vocabularyUrl": "%s/@@getVocabulary?name=collective.object.collection&field=identification_identification_collections", "initialValues": {}, "separator": "_"}' % (context_url)
            },
            'physicalCharacteristics_materials': {
                'data': '{"orderable": true, "vocabularyUrl": "%s/@@getVocabulary?name=collective.object.materials&field=material", "initialValues": {}, "separator": "_"}' % (context_url)
            },
            'physicalCharacteristics_techniques': {
                'data': '{"orderable": true, "vocabularyUrl": "%s/@@getVocabulary?name=collective.object.techniques&field=technique", "initialValues": {}, "separator": "_"}' % (context_url)
            },
            'identification_objectName_objectname_type': {
                'data':'{"orderable": true, "vocabularyUrl": "%s/@@getVocabulary?name=collective.object.objectname_type&field=types", "initialValues": {}, "separator": "_"}' % (context_url)
            },
            'identification_objectName_objectname': {
                'data':'{"orderable": true, "vocabularyUrl": "%s/@@getVocabulary?name=collective.object.objectname&field=types", "initialValues": {}, "separator": "_"}' % (context_url)
            }
        }
        
        searchFilters = []
        registry = getUtility(IRegistry)
        searchFiltersRecord = registry['advancedsearch.fields']
        if searchFiltersRecord:
            filters = list(searchFiltersRecord)
            if filters:
                for advanced_filter in filters:
                    if advanced_filter != "":
                        is_widget = False
                        data_select = ""
                        if advanced_filter in advanced_widgets:
                            is_widget = True
                            data_select = advanced_widgets[advanced_filter]['data']

                        new_filter = {
                            "name": advanced_filter,
                            "is_widget": is_widget,
                            "select2_data": data_select
                        }

                        searchFilters.append(new_filter)
                    else:
                        continue
            else:
                return searchFilters

        return searchFilters
