#!/usr/bin/python
# -*- coding: utf-8 -*-


import re
import json
from plone.app.layout.viewlets.common import FooterViewlet
from plone.app.layout.viewlets.common import ViewletBase
from Products.Five import BrowserView
from AccessControl import getSecurityManager
from Products.CMFPlone.PloneBatch import Batch
from Products.CMFCore.permissions import ModifyPortalContent
from plone.dexterity.browser.view import DefaultView
from plone.app.contentlisting.interfaces import IContentListing
from Products.ZCTextIndex.ParseTree import ParseError

from Products.CMFCore.utils import getToolByName
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from plone.app.portlets.interfaces import IColumn
from zope.interface import Interface
from plone.portlets.interfaces import IPortletManager
from plone.memoize.instance import memoize
from zope.component import getMultiAdapter
from collective.portletpage.browser.portletpage import TwoColumns
from plone.portlet.collection import collection as base
from plone.app.search.browser import Search
from plone.app.layout.viewlets.common import GlobalSectionsViewlet
from plone.app.i18n.locales.browser.selector import LanguageSelector
from zope.component import queryAdapter
from plone.multilingual.interfaces import ITG
from plone.multilingual.interfaces import NOTG
from plone.app.multilingual.browser.selector import getPostPath, addQuery
from plone.app.portlets.browser.manage import ManageContextualPortlets
from collective.portletpage.browser.interfaces import IManagePortletPagePortletsView

from zope.component import getUtility
from plone.registry.interfaces import IRegistry
from collective.leadmedia.interfaces import ICanContainMedia
from zope.interface import implements
from plone.app.uuid.utils import uuidToCatalogBrain, uuidToObject
from z3c.relationfield.interfaces import IRelationValue
from plone.app.layout.viewlets.content import DocumentBylineViewlet
from Acquisition import aq_parent, aq_inner
from Products.CMFPlone.interfaces import IPloneSiteRoot

SHOP_AVAILABLE = True

try:
    from bda.plone.cart import get_item_data_provider
    from bda.plone.shop.interfaces import IBuyable
except ImportError:
    SHOP_AVAILABLE = False

from decimal import Decimal

try:
    from Products.PloneGetPaid.interfaces import IBuyableMarker
    from Products.PloneGetPaid.interfaces import PayableMarkerMap
    from Products.PloneGetPaid.interfaces import IPayableMarker
    GETPAID_EXISTS = True
except ImportError:
    GETPAID_EXISTS = False


class CommonBrowserView(BrowserView):
    """
    Common utilities for all the other views
    """
    nxt = None
    prv = None
    
    def showManageButton(self):
        secman = getSecurityManager()
        if not secman.checkPermission('Portlets: Manage portlets', self.context):
            return False
        else:
            return True
        
    def addPaypalButton(self, label, name, price):
        return """
            <form action="https://www.paypal.com/cgi-bin/webscr" method="post" onSubmit="return Arnolfini.trackEcommerce('%(name)s', '%(price).2f', 'Book')">
                <input name="business" type="hidden" value="general@intk.com" />
                <input name="amount" type="hidden" value="%(price).2f" />
                <input name="item_name" type="hidden" value="%(name)s" />
                <input name="no-shipping" type="hidden" value="1" />
                <input name="currency_code" type="hidden" value="GBP" />
                <input name="cpp_header_image" type="hidden" value="http://new.arnolfini.org.uk/++resource++plonetheme.arnolfini.images/arnolfiniLogo.png" />
                <input name="return" type="hidden" value="http://www.arnolfini.org.uk/purchase/thank-you/" />
                <input name="cmd" type="hidden" value="_xclick" />
                <input type="submit" value="%(label)s" />
            </form>
        """%{"price": price, "name": name, "label": label}
    
    def payable(self, item):
        """Return the payable (shippable) version of the context.
        """
        if GETPAID_EXISTS:
            iface = PayableMarkerMap.get(IBuyableMarker, None)
            if iface is None:
                print("Something is badly wrong here.")
                return None
            return iface( item )
        else:
            return none
        
    def checkPermission(self, item, permission):
        secman = getSecurityManager()
        return secman.checkPermission(permission, item)
    
    def getTagsAsClass(self, item):
        
        classes = []
        for tag in item.Subject:
            classes.append("tag_%s"%tag.replace(" ", "_"))
        
        return " ".join(classes)

    def hasVideoTag(self, item):
        classes = []
        
        if not hasattr(item, 'getURL'):
            uuid = item.UID()
            item = uuidToCatalogBrain(uuid)
        
        for tag in item.Subject:
            if tag == "video":
                return True

        return False
    
    def slideshow(self, parent):
        """
        Creates a slideshow with the media from parent
        """
        parentURL = parent.absolute_url()
        structure = """
        <div class="embededMediaShow">
            <a  href="%s?recursive=true">slideshow</a>
        </div>
        """%parentURL
        
        return structure
    
    def checkYoutubeLink(self, link):
        """
        Check if a URL is a youtube video
        """
        isYoutube = link.find("youtube") != -1
        youtubeId = ""
        amp = link.find("&")
    
        if isYoutube and amp != -1:
            youtubeId = link[link.find("?v=")+3:amp]
        elif isYoutube and amp == -1:
            youtubeId = link[link.find("?v=")+3:]
    
        return isYoutube, youtubeId
        
    def checkVimeoLink(self, link):
        """
        Check if URL is a vimeo video
        """
        isVimeo = link.find("vimeo") != -1
        vimeoId = ""
        
        if isVimeo:
            vimeoId = link.split("vimeo.com/")[1]
            
        return isVimeo, vimeoId
    
    def getLeadMediaTag(self, item, scale="large"):
        if item.portal_type == 'Link':
            isYoutube, youtubeId = self.checkYoutubeLink(item.getRemoteUrl)
            isVimeo, vimeoId = self.checkVimeoLink(item.getRemoteUrl)
            embed = ""
            
            if isYoutube:
                return '<iframe id="'+youtubeId+'" width="100%" height="393" src="http://www.youtube.com/embed/'+youtubeId+'?rel=0&enablejsapi=1" frameborder="0" allowfullscreen></iframe>'
            elif isVimeo:
                return '<iframe src="http://player.vimeo.com/video/'+vimeoId+'?title=0&amp;byline=0&amp;portrait=0" width="100%" height="393" frameborder="0"></iframe>'

        if item.portal_type == 'Image':
            if hasattr(item, 'getURL'):
                lead = item.getURL()
            else:
                lead = item.absolute_url()
        
        elif hasattr(item, 'leadMedia'):
            leadUID = item.leadMedia
            leadBrain = uuidToCatalogBrain(leadUID)
            if leadBrain:
                lead = leadBrain.getURL()
            else:
                lead = None
        else:
            brains = uuidToCatalogBrain(item.UID())
            if brains:
                leadUID = brains.leadMedia
                leadBrain = uuidToCatalogBrain(leadUID)
                if leadBrain:
                    lead = leadBrain.getURL()
                else:
                    lead = None
            else:
                lead = None

        if lead is not None:
            crop = ""
            if hasattr(item, 'getURL'):
                return '<img src="%(url)s" alt="%(title)s" title="%(title)s" />%(crop)s'%{'url': "%s/@@images/image/%s"%(lead, scale), 'title':item.Title(), 'crop':crop}
            else:
                return '<img src="%(url)s" alt="%(title)s" title="%(title)s" />%(crop)s'%{'url': "%s/@@images/image/%s"%(lead, scale), 'title':item.Title(), 'crop':crop}


    def containsMedia(self, item):
        if item.portal_type == "Collection":
            return len(self.getCollectionMedia(item)) > 0
        
        if hasattr(item, 'leadMedia'):
            return item.leadMedia != None
        else:
            uuid = item.UID()
            brains = uuidToCatalogBrain(uuid)
            if brains:
                return brains.leadMedia != None
            else:
                return False
    
    def getPressKit(self, item):
        if item.restrictedTraverse('@@plone').isStructuralFolder():
            catalog = getToolByName(self.context, 'portal_catalog')
            plone_utils = getToolByName(self.context, 'plone_utils')
                
            path = '/'.join(item.getPhysicalPath())
            sm = getSecurityManager() 
            
            results = catalog.searchResults(path = {'query' : path}, portal_type = 'Press Kit')
            
            for result in results:
                if sm.checkPermission('View', result):
                    return result
            
            return None
        else:
            return None
    
    def trimText(self, text, limit, strip=False):
        if text != None:
            if strip:
                text = self.stripTags(text)
        
            if len(text) > limit: 
                res = text[0:limit]
                lastspace = res.rfind(" ")
                res = res[0:lastspace] + " ..."
                return res
            else:
                return text
        else:
            return ""
            
    def stripTags(self, text):
        return re.sub('<[^<]+?>', '', text)
    
    def getTwoWayRelatedContent(self):
        """
        Gets all the manually related content both related items of the current context and items where the current context is marked as related.
        """
        filtered = []
        related = []
        related = self.context.getRefs()
        backRelated = self.context.getBRefs()
        
        related.extend(backRelated)
        
        result = self._uniq(related);
        
        for res in result:
            if self.checkPermission(res, 'View'):
                filtered.append(res)
                
        return filtered
        
    def getContentAsLinks(self, content):
        """
        A commodity, this formats a content list as an HTML structure of titles with links. Comma separated. Used to list the artists related to an exhibition.
        """
        result = []
        workflow = getToolByName(self.context,'portal_workflow')
        sortedContent = sorted(content, key=lambda res: res.portal_type == 'Media Person' and self._normalizePersonName(res.title) or res.title)
        for res in sortedContent:
            if self.checkPermission(res, 'View'):
                if res.portal_type == 'Media Person':
                    result.append('<a href="%(link)s" class="%(state_class)s">%(title)s</a>'%{'link':res.absolute_url(), 'title':self._normalizePersonName(res.title), 'state_class': 'state-' + queryUtility(IIDNormalizer).normalize(workflow.getInfoFor(res,'review_state'))})
                else:
                    result.append('<a href="%(link)s" class="%(state_class)s">%(title)s</a>'%{'link':res.absolute_url(), 'title':res.title, 'state_class': 'state-' + queryUtility(IIDNormalizer).normalize(workflow.getInfoFor(res,'review_state'))})               
        
        return ", ".join(result)
    
    def getTwoWayRelatedContentOfType(self, typeList):
        result = []
        for res in self.getTwoWayRelatedContent():
            if res.portal_type in typeList:
                result.append(res)
                
        return result
    
    def _normalizePersonName(self, person):
        names = person.split(",")
        if len(names) == 2:
            return "%s %s"%(names[1], names[0])
        else:
            return person
          
    def isEventPast(self, event):
        """
        Checks if the event is already past
        """
        if event.portal_type != 'Event' and event.portal_type != 'Media Event':
            return False
        else:
            t = DateTime(time.time())
            if event.end() is not None:
                end = DateTime(event.end())
                return end.year() < t.year() or (end.year() == t.year() and end.month() < t.month()) or(end.year() == t.year() and end.month() == t.month() and end.day() < t.day())
            else:
                start = DateTime(event.start())
                return start.year() < t.year() or (start.year() == t.year() and start.month() < t.month()) or(start.year() == t.year() and start.month() == t.month() and start.day() < t.day())
            
    
    def getCurrentTime(self):
        """
        Utility, returns a current DateTime object.
        """
        return DateTime()
    
    def getFormattedEventDate(self, event):
        """
        Formats the start and end dates properly and marks the event as past or future
        """
        if event.portal_type != 'Event' and event.portal_type != 'Media Event':
            return ""
        
        if event.start() is None or event.end() is None:
            if event.start() is None and event.end() is None:
                return ""
            else:
                samedate = True
        else:
            samedate = event.start().strftime('%d - %m - %Y') == event.end().strftime('%d - %m - %Y')
            
        exceptions = ""
        
        if hasattr(event, 'exceptions'):
            exceptions = event.exceptions
            
        finalDatesFmt = '<div class="dates %(class)s"><span class="dateText">%(dates)s%(hours)s %(exceptions)s</span></div>'
        
        dates = "%s"%(samedate and (event.start() is not None and event.start().strftime('%A %d %B %Y') or event.end().strftime('%A %d %B %Y')) or "%s to %s"%(event.start().strftime('%A %d %B %Y'), event.end().strftime('%A %d %B %Y')))
        
        openingHour = event.start() is not None and event.start().strftime('%H:%M') or ""
        closingHour = event.end() is not None and event.end().strftime('to %H:%M') or ""
        hoursExist = 'to %s'%openingHour != closingHour
        
        hours = hoursExist and '<span class="hours">, %s %s</span>'%(openingHour, closingHour) or '<span class="hours">, %s</span>'%openingHour
        
        finalDates = finalDatesFmt%{'class': self.isEventPast(event) and 'past' or 'future', 'dates': dates, 'hours': hours, 'exceptions':exceptions}
        
        return finalDates
            
    def isBuyable(self, item):
        """
        Check if an item is buyable with PloneGetPaid
        """
        if not GETPAID_EXISTS:
            return False
        else:
            return IBuyableMarker.providedBy(item)

    def getPrice(self, item):
        if SHOP_AVAILABLE:
            item_data = get_item_data_provider(item)
            net_price = Decimal(item_data.net)
            vat = item_data.vat
            if vat % 2 != 0:
                item_vat = Decimal(vat).quantize(Decimal('1.0'))
            else:
                item_vat = Decimal(vat)
            
            gross_price = net_price + net_price / Decimal(100) * item_vat
            return gross_price
        else:
            return float(0.0)
    
    def getEventBookingLink(self, event):
        """
        Check if the booking information is a link or just a code. return a full url
        """
        if not event.getBooking():
            return ""
        else:
            if event.getLink().find("http://") != -1:
                return event.getLink()
            else:
                return 'http://purchase.tickets.com/buy/TicketPurchase?agency=ARNOLFINI&organ_val=26385&schedule=list&event_val=%s'%event.getLink()
      
    def _uniq(self, alist):    # Fastest order preserving
        set = {}
        return [set.setdefault(e,e) for e in alist if e not in set]

class SearchView(CommonBrowserView, Search):
    """
    Adding to Search view
    """

    def results(self, query=None, batch=True, b_size=10, b_start=0):
        """Get properly wrapped search results from the catalog.
        Everything in Plone that performs searches should go through this view.
        'query' should be a dictionary of catalog parameters."""
        
        if query is None:
            query = {}
        if batch:
            query['b_start'] = b_start = int(b_start)
            query['b_size'] = b_size

        query = self.filter_query(query)

        if query is None:
            results = []
        else:
            ## Needs fix
            """if 'identification_identification_objectNumber' in query:
                query['identification_identification_objectNumber'] = query['identification_identification_objectNumber'].lower()

            if 'identification__identification_collections' in query:
                query['identification__identification_collections'] = query['identification__identification_collections'].split("_")

            if 'physicalCharacteristics__material' in query:
                query['physicalCharacteristics__material'] = query['physicalCharacteristics__material'].split("_")

            if 'physicalCharacteristics__technique' in query:
                query['physicalCharacteristics__technique'] = query['physicalCharacteristics__technique'].split("_")
            
            if 'identification__objectName_objectname_type' in query:
                query['identification__objectName_objectname_type'] = query['identification__objectName_objectname_type'].split("_")"""

            catalog = getToolByName(self.context, 'portal_catalog')
            try:
                results = catalog(**query)
            except ParseError:
                return []
            except UnicodeDecodeError:
                return []

        results = IContentListing(results)
        if batch:
            results = Batch(results, b_size, b_start)

        return results

    def getItemTitle(self, item):
        title = item.Title()

        if item.portal_type == "Object":
            try:
                if item.identification_identification_objectNumber:
                    title = "%s - %s" %(item.identification_identification_objectNumber.encode('ascii','ignore'), title.encode('ascii', 'ignore'))
            except:
                title = item.Title()

        return title

    def getAdvancedButtonQuery(self):
        try:
            params = self.request.form.items()

            registry = getUtility(IRegistry)
            searchFiltersRecord = registry['advancedsearch.fields']
            q = ""

            if searchFiltersRecord:
                advancedfields = list(searchFiltersRecord)
                advancedfields.append("SearchableText")
                q = "&".join(["%s=%s" %(param,value) for param,value in params if param in advancedfields and value])

            return q
        except:
            return ""

    def getExtraFilters(self):
        params = self.request.form.items()
        extra_filters = []

        # Needs fix
        widget_fields = ['identification_identification_collection', 'physicalCharacteristics_materials',
                         'physicalCharacteristics_techniques', 'identification_objectName_objectname_type']


        new_params = []
        for k, v in params:
            if k != "path":
                new_params.append((k,v))
            else:
                if type(v) is list:
                    for p in v:
                        new_params.append(('path:list', p))
                else:
                    new_params.append((k,v))

        params = new_params

        registry = getUtility(IRegistry)
        try:
            searchFiltersRecord = registry['advancedsearch.fields']
        except:
            return []

        if searchFiltersRecord:
            advancedfields = list(searchFiltersRecord)
            advancedfields.append('path')

            for param, value in params:
                if param in advancedfields:
                    if value:
                        if type(value) == list:
                            continue
                        if param in widget_fields:
                            list_fields = value.split("_")
                            curr = 0
                            for field in list_fields:
                                curr += 1
                                q = "&".join(["%s=%s" %(p, v) for p, v in params if p != param and p not in ['created']])

                                new_list_field = [f for f in list_fields if f != field]
                                new_string = "_".join(new_list_field)
                                q += "&%s=%s" %(param, new_string)

                                search_filter = {}
                                if curr > 1:
                                    search_filter["param"] = ''
                                else:
                                    search_filter["param"] = param
                                search_filter["value"] = field
                                search_filter["link"] = self.context.absolute_url()+"/@@search?%s" %(q)
                                extra_filters.append(search_filter)
                        else:
                            q = "&".join(["%s=%s" %(p, v) for p, v in params if p != param and p not in ['created']])
                            search_filter = {}
                            search_filter["param"] = param
                            search_filter["value"] = value
                            search_filter["link"] = self.context.absolute_url()+"/@@search?%s" %(q)
                            extra_filters.append(search_filter)
                            
        return extra_filters

    def checkUserPermission(self):
        sm = getSecurityManager()
        if sm.checkPermission(ModifyPortalContent, self.context):
            return True
        return False

    def getSearchFilters(self):
        searchFilters = []
        registry = getUtility(IRegistry)
        searchFiltersRecord = registry['searchfilters.folders']
        if searchFiltersRecord:
            filters = list(searchFiltersRecord)

            if filters:
                for uid in filters:
                    item = uuidToCatalogBrain(uid)
                    if item:
                        searchFilters.append({"name": item.Title, "path": item.getPath()})

        return searchFilters
    
class PagePortletView(ViewletBase):
    """
    helper classes for pagePortlet
    """
    def showManageButton(self):
        secman = getSecurityManager()
        if not secman.checkPermission('Portlets: Manage portlets', self.context):
            return False
        else:
            return True

class FooterView(FooterViewlet):
    """
    helper classes for footer
    """
    def showManageButton(self):
        secman = getSecurityManager()
        if not secman.checkPermission('Portlets: Manage portlets', self.context):
            return False
        else:
            return True

class FolderListing(CommonBrowserView):
    """'
    Override of folder_listing view
    """

    collection_template = ViewPageTemplateFile('templates/collection_custom.pt')
    folder_template = ViewPageTemplateFile('templates/folder_custom.pt')

    def results(self, batch=True, b_start=0):
        results = []

        if self.context.portal_type  == 'Collection':
            sort_on = getattr(self.context, 'sort_on', 'sortable_title')
            pagesize = getattr(self.context, 'item_count', 33)
            results = self.context.results(batch=batch, b_size=pagesize, sort_on=sort_on, b_start=b_start)
            return results

        elif self.context.portal_type in ['Folder', 'Press Kit']:
            brains = self.context.getFolderContents()
            final_res = list(brains)
            
            if batch:
                results = Batch(final_res, pagesize, start=b_start)
            else:
                return final_res

        return results

    def getImageObject(self, item):
        if item.portal_type == "Image":
            return item.getObject()
        if item.leadMedia != None:
            uuid = item.leadMedia
            media_object = uuidToCatalogBrain(uuid)
            if media_object:
                return media_object.getURL()+"/@@images/image/mini"
            else:
                return None
        else:
            return None

    def isBuyable(self, item):
        if SHOP_AVAILABLE:
            return IBuyable.providedBy(item)
        else:
            return False

    def getPrice(self, item):
        if SHOP_AVAILABLE:
            item_data = get_item_data_provider(item)
            net_price = Decimal(item_data.net)
            vat = item_data.vat
            if vat % 2 != 0:
                item_vat = Decimal(vat).quantize(Decimal('1.0'))
            else:
                item_vat = Decimal(vat)
            
            gross_price = net_price + net_price / Decimal(100) * item_vat
            return gross_price
        else:
            return float(0.0)

    def getItemURL(self, item, item_url):
        if item.portal_type == "Image":
            obj = item.getObject()
            img = getattr(obj, 'image', None)
            if not img:
                new_url = "%s/view" %(item_url)
                return new_url

        return item_url

    def __call__(self):
        """"""
        portal_type = self.context.portal_type
        if portal_type == "Folder":
            return self.folder_template()
        else:
            return self.collection_template()

class CollectionPortlet(base.Renderer, FolderListing):
    """
        Extend portlet base renderer
    """
    _template = ViewPageTemplateFile("alternative_templates/portletcollection.pt")
    render = _template

class ContentView(BrowserView):

    def getFBdetails(self):
        item = self.context
        
        uid = item.UID()

        item_brain = uuidToCatalogBrain(uid)

        details = {}    
        details["title"] = item.Title()
        details["type"] = "article"
        details["site_name"] = "Teylers Museum"
        details["url"] = item.absolute_url()
        details["description"] = item.Description()
        details["double_image"] = ""
        details["image"] = ""

        if getattr(item_brain, "leadMedia", None) != None:
            image = uuidToCatalogBrain(item_brain.leadMedia)
            details["image"] = image.getURL()+'/@@images/image/large'
        else:
            details["image"] = ""

        return details

    def showManageButton(self):
        secman = getSecurityManager()
        if not secman.checkPermission('Portlets: Manage portlets', self.context):
            return False
        else:
            return True


class NumberOfResults(CommonBrowserView):
    """
    Called by AJAX to know how many results in the collection. Returns JSON.
    """
    def getJSON(self):
        callback = hasattr(self.request, 'callback') and 'json' + self.request['callback'] or None
        only_documented = not hasattr(self.request, 'only_documented') 
        
        result = None
        
        if self.context.portal_type == 'Collection':
            brains = self.context.queryCatalog(batch=False)
            if only_documented:
                result = []
                for res in brains:
                    if res.leadMedia:
                        result.append(res)
    
        if result is not None:
            jsonStr = json.dumps(len(result))
        else:
            jsonStr = json.dumps(result)
            
        if callback is not None:
            return callback +'(' + jsonStr + ')'
        else:
            return jsonStr

class get_image_resolution(BrowserView):
    """
    Called by AJAX to know original resolution of image.
    """
    def get_image_resolution(self):
        result = {"success": False}

        if self.context.portal_type == "Image":
            ob = self.context
            if ob.image != None:
                result["success"] = True
                w, h = ob.image.getImageSize()
                result["w"] = w
                result["h"] = h
        
        jsonStr = json.dumps(result)
        return jsonStr

class CustomManagePortlets(ManageContextualPortlets):
    """View used for the edit screen
    """
    implements(IManagePortletPagePortletsView)

    def __init__(self, context, request):
        # Skip past the main parent constructor, since it sets disable_border
        super(ManageContextualPortlets, self).__init__(context, request)



class TableView(BrowserView):
    index_folder = ViewPageTemplateFile('templates/table_view.pt')
    index_collection = ViewPageTemplateFile('templates/table_collection_view.pt')
    index_tabular_collection = ViewPageTemplateFile('templates/tabular_collection_view.pt')

    def getMaker(self, item):
        obj = item.getObject()

        try:
            if hasattr(obj, 'productionDating_productionDating'):
                terms = []
                production = obj.productionDating_productionDating
                for line in production:
                    if 'makers' in line:
                        makers = line['makers']
                        for maker in makers:
                            if IRelationValue.providedBy(maker):
                                maker_obj = maker.to_object
                                title = getattr(maker_obj, 'title', "")
                                terms.append(title)
                            elif getattr(maker, 'portal_type', "") == "PersonOrInstitution":
                                title = getattr(maker, 'title', "")
                                terms.append(title)
                            else:
                                continue

                structure = "<br>".join(terms)
                return structure
        except:
            return ""
        return ""

    def getLeadMedia(self, UID):
        if UID:
            leadBrain = uuidToCatalogBrain(UID)
            if leadBrain:
                lead = leadBrain.getURL()
                lead_crop = "%s/@@images/image/mini" %(lead)
                return lead_crop
        return ""

    def getCurrLocation(self, data):
        try:
            result = ""

            result = '<br>'.join(data)

            return result
        except:
            return ""

    def getYear(self, item):
        obj = item.getObject()

        if hasattr(obj, 'titleAuthorImprintCollation_imprint_year'):
            year = obj.titleAuthorImprintCollation_imprint_year
            return year
        else:
            return None

    def getAuthor(self, context_author, item):

        fieldnames = {
            "Book":"titleAuthorImprintCollation_titleAuthor_author",
            "Audiovisual":"titleAuthorImprintCollation_titleAuthor_author",
            "Article":"titleAuthorSource_titleAuthor_author",
            "Serial":"titleAuthorImprintCollation_titleAuthor_author",
            "Resource":"resourceDublinCore_creators"
        }

        obj = item.getObject()
        obj_portal_type = obj.portal_type;

        author_field = ""
        if obj_portal_type in fieldnames:
            author_field = fieldnames[obj_portal_type]

        if author_field:
            if hasattr(obj, author_field):
                authors = getattr(obj, author_field, "")
                if authors:
                    author = authors[0]

                    if obj_portal_type == "Resource":
                        authors_list = author
                    else:
                        if 'authors' in author:
                            authors_list = author['authors']
                        else:
                            authors_list = None

                    if authors_list:
                        if obj_portal_type == "Resource":
                            author_person = authors_list
                        else:
                            author_person = authors_list[0]

                        portal_type = getattr(author_person, 'portal_type', '')
                        author_url = ""
                        author_name = ""

                        if IRelationValue.providedBy(author_person):
                            person = author_person.to_object
                            author_url = person.absolute_url()
                            author_name = getattr(person, 'title', '')

                        elif portal_type == "PersonOrInstitution":
                            author_url = author_person.absolute_url()
                            author_name = getattr(author_person, 'title', '')

                        final_author = "<a href='%s'>%s</a>" %(author_url, author_name)
                        return final_author
                    else:
                        return ""
                else:
                    return ""
            else:
                return context_author.get('name_or_id', None)
        else:
            return context_author.get('name_or_id', None)

    def __call__(self):
        if self.context.portal_type == "Collection" and '/bibliotheek' in self.context.absolute_url():
            return self.index_collection()
        elif self.context.portal_type == "Collection":
            return self.index_tabular_collection()
        else:
            return self.index_folder()


class ObjectFields(DefaultView):
    def getJSON(self):
        data = []
        from zope.i18nmessageid import MessageFactory

        if self.context.portal_type == "Object":
            _ = MessageFactory('collective.object')
        elif self.context.portal_type == "Book":
            _ = MessageFactory('collective.bibliotheek')
        else:
            _ = MessageFactory('collective.objec')

        for widget in self.widgets.values():
            try:
                _label = _(widget.label)
                label = self.context.translate(_label)
                new_field = {label:widget.value}
                json.dumps(new_field)
                data.append(new_field)
            except:
                _label = _(widget.label)
                label = self.context.translate(_label)
                new_field = {label:str(widget.value)}
                data.append(new_field)
                
        for group in self.groups:
            new_group = []
            for widget in group.widgets.values():
                try:
                    _label = _(widget.label)
                    label = self.context.translate(_label)
                    new_field = {label:widget.value}
                    json.dumps(new_field)
                    new_group.append(new_field)
                except:
                    _label = _(widget.label)
                    label = self.context.translate(_label)
                    new_field = {label:str(widget.value)}
                    new_group.append(new_field)

            _group_label = _(group.label)
            group_label = self.context.translate(_group_label)
            data.append({group_label:new_group})

        result = json.dumps(data)
        return result


class CustomDocumentByLineViewlet(DocumentBylineViewlet):
    render = ViewPageTemplateFile("templates/document_byline.pt")

    def parent_url(self):
        """
        """
        context = aq_inner(self.context)
        portal_membership = getToolByName(context, 'portal_membership')

        obj = context

        checkPermission = portal_membership.checkPermission

        # Abort if we are at the root of the portal
        if IPloneSiteRoot.providedBy(context):
            return None

        # Get the parent. If we can't get it (unauthorized), use the portal
        parent = aq_parent(obj)

        # We may get an unauthorized exception if we're not allowed to access
        # the parent. In this case, return None
        try:
            if getattr(parent, 'getId', None) is None or \
                    parent.getId() == 'talkback':
                # Skip any Z3 views that may be in the acq tree;
                # Skip past the talkback container if that's where we are
                parent = aq_parent(parent)

            if not checkPermission('List folder contents', parent):
                return None

            return parent.absolute_url()
        except Unauthorized:
            return None

    







