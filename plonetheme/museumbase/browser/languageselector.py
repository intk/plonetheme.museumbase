#!/usr/bin/env python
# -*- coding: utf-8 -*

from plone.app.multilingual.browser.selector import LanguageSelectorViewlet
from plone.memoize import view

class LanguageSelector(LanguageSelectorViewlet):
	
	@view.memoize
	def extra_languages(self):

		catalog = self.context.portal_catalog
		instance = "NewTeylers"
		if "/zm" in self.context.absolute_url():
			instance = "zm"

		extra_languages = []

		path = "/%s/shared/lang" %(instance)
		results = catalog(portal_type="Document", path=path, sort_on="getObjPositionInParent")

		if len(results) > 0:
			for brain in results:
				url = brain.getObject().absolute_url()
				extra_languages.append({
					"title": brain.Title,
					"url": url
					})

		return extra_languages