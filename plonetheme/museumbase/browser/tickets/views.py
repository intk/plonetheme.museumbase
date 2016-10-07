#!/usr/bin/env python
# -*- coding: utf-8 -*
from Acquisition import aq_inner
from plone.app.uuid.utils import uuidToObject, uuidToCatalogBrain
from bda.plone.cart.browser import CartView
from bda.plone.orders.browser.views import OrderView, OrdersViewBase, OrdersView
from bda.plone.orders.browser.views import OrdersTable
from bda.plone.orders.browser.views import OrdersData
from bda.plone.orders.browser.views import TableData
from bda.plone.orders.browser.views import vendors_form_vocab
from bda.plone.orders.browser.views import customers_form_vocab
from bda.plone.orders.browser.views import Translate
from bda.plone.orders.browser.views import SalariedDropdown
from bda.plone.orders.browser.views import StateDropdown
from bda.plone.orders.common import OrderData
from bda.plone.orders.common import get_bookings_soup
from bda.plone.orders.common import get_order
from bda.plone.orders.common import get_orders_soup
from bda.plone.orders.common import get_vendor_by_uid
from bda.plone.orders.common import get_vendor_uids_for
from bda.plone.orders.common import get_vendors_for
from bda.plone.orders.interfaces import IBuyable
from repoze.catalog.query import Any
from repoze.catalog.query import Contains
from repoze.catalog.query import Eq
from repoze.catalog.query import Ge
from repoze.catalog.query import Le

from bda.plone.cart import get_object_by_uid
from bda.plone.cart import ascur
from decimal import Decimal 
from bda.plone.orders.common import get_vendors_for
from Products.Five import BrowserView
from bda.plone.orders import message_factory as _
from Products.CMFPlone.interfaces import IPloneSiteRoot


from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
import urllib
import plone.api
from yafowil.utils import Tag

from souper.soup import get_soup
from souper.soup import LazyRecord

from bda.plone.orders import vocabularies as vocabs
from bda.plone.orders import interfaces as ifaces

from Products.CMFCore.utils import getToolByName
from plone.app.layout.navigation.interfaces import INavigationRoot
from Products.CMFCore.interfaces import ISiteRoot

import json

DT_FORMAT = '%d.%m.%Y'

###
### Redeem view
###
class RedeemViewBase(OrdersViewBase):
    table_view_name = '@@redeemtable'

    def redeem_table(self):
        return self.context.restrictedTraverse(self.table_view_name)()

class RedeemView(OrdersView):
    table_view_name = '@@redeemtable'

    def redeem_table(self):
        return self.context.restrictedTraverse(self.table_view_name)()

    def __call__(self):
        # check if authenticated user is vendor
        if not get_vendors_for():
            raise Unauthorized
        return super(RedeemView, self).__call__()


class RedeemTableBase(BrowserView):
    table_template = ViewPageTemplateFile('templates/table.pt')
    table_id = 'bdaploneorders'
    data_view_name = '@@redeemdata'

    def rendered_table(self):
        return self.table_template(self)

    def render_filter(self):
        return None

    def render_order_actions_head(self):
        return None

    def render_order_lastname_head(self):
        return None

    def render_order_firstname_head(self):
        return None

    def render_redeem_head(self):
        return None

    def render_order_uid_head(self):
        return None

    def render_booking_title_head(self):
        return None

    def render_order_actions(self, colname, record):
        return None

    def render_salaried(self, colname, record):
        value = ""
        return value

    def render_state(self, colname, record, redeem_state, uid=None):
        state = redeem_state
        return translate(vocabs.state_vocab()[state],
                         context=self.request)

    def render_order_firstname(self, colname, record):
        order = OrderData(self.context, uid=record.attrs['order_uid'])
        name = order.order.attrs.get('personal_data.firstname', '')
        if name:
            value = name
        return value

    def render_order_lastname(self, colname, record):
        order = OrderData(self.context, uid=record.attrs['order_uid'])
        name = order.order.attrs.get('personal_data.lastname', '')
        if name:
            value = name
        return value

    def render_dt(self, colname, record):
        order = OrderData(self.context, uid=record.attrs['order_uid'])
        value = order.order.attrs.get(colname, '')
        if value:
            value = value.strftime(DT_FORMAT)
        return value

    def render_booking_title(self, colname, record):
        booking_title = record.attrs['title']
        value = str(booking_title)
        return value

    def render_booking_redeem(self, colname, record):
        return ''

    def render_order_uid(self, colname, record):
        booking_uid = record.attrs['uid']
        value = str(booking_uid)
        return value

    @property
    def ajaxurl(self):
        site = plone.api.portal.get()
        return '%s/%s' % (self.context.absolute_url(), self.data_view_name)

    @property
    def columns(self):
        return [{
            'id': 'actions',
            'label': _('actions', default=u'Actions'),
            'head': self.render_order_actions_head,
            'renderer': self.render_order_actions,
        }, {
            'id': 'uid',
            'label': _('Ticket UID', default=u'Ticket UID'),
            'head': self.render_order_uid_head,
            'renderer': self.render_order_uid,
        }, {
            'id': 'title',
            'label': _('Title', default=u'Title'),
            'head': self.render_booking_title_head,
            'renderer': self.render_booking_title,
        }, 
        {
            'id': 'created',
            'label': _('date', default=u'Date'),
            'renderer': self.render_dt,
        }, {
            'id': 'personal_data.firstname',
            'label': _('firstname', default=u'First Name'),
            'head': self.render_order_firstname_head,
            'renderer': self.render_order_firstname
        },
        {
            'id': 'personal_data.lastname',
            'label': _('lastname', default=u'Last Name'),
            'head': self.render_order_lastname_head,
            'renderer': self.render_order_lastname
        },         
        {
            'id': 'state',
            'label': _('state', default=u'State'),
            'renderer': self.render_state,
        }
        ]
        
class RedeemDropdown(object):
    render = ViewPageTemplateFile('templates/dropdown.pt')
    name = ''
    css = 'dropdown'
    action = ''
    vocab = {}
    transitions = {}
    value = ''

    def __init__(self, context, request, record, redeem_state, ticket_uid):
        self.context = context
        self.request = request
        self.record = record
        self.ticket_uid = ticket_uid
        self.redeem_state = redeem_state

    @property
    def booking_data(self):
        return self.record

    def create_items(self, transitions):
        ret = list()
        url = self.context.absolute_url()
        # create and return available transitions for order
        uid = str(self.record.attrs['uid'])
        order_uid = str(self.record.attrs['order_uid'])
        vendor = self.request.form.get('vendor', '')
        
        for transition in transitions:
            target = '%s?transition=%s&uid=%s&ticket_uid=%s&order_uid=%s' % (url, transition, uid, self.ticket_uid, order_uid)
            ret.append({
                'title': self.transitions[transition],
                'target': target,
            })
        return ret

    @property
    def identifyer(self):
        return '%s-%s' % (self.name, str(self.ticket_uid))

    @property
    def ajax_action(self):
        return '%s:#%s-%s:replace' % (self.action,
                                      self.name,
                                      str(self.ticket_uid))

    @property
    def items(self):
        raise NotImplementedError(u"Abstract Dropdown does not implement "
                                  u"``items``.")


class RedeemStateDropdown(RedeemDropdown):
    name = 'state'
    css = 'dropdown change_order_state_dropdown'
    action = 'redeemtransition'
    vocab = vocabs.state_vocab()
    transitions = vocabs.state_transitions_vocab()

    @property
    def value(self):
        return self.redeem_state

    @property
    def items(self):
        state = self.redeem_state
        transitions = list()
        if state in [ifaces.STATE_NEW, ifaces.STATE_RESERVED]:
            transitions = [
                ifaces.STATE_TRANSITION_REDEEM
            ]
        else:
            transitions = [ifaces.STATE_TRANSITION_RENEW]
        return self.create_items(transitions)

class RedeemTransition(BrowserView):
    dropdown = None

    def do_ticket_transaction(self, transaction, ticket_uid, ticket_booking):
        ticket_state = 'new'

        if transaction == 'redeem':
            to_redeem = ticket_booking.attrs.get('to_redeem', '')
            if to_redeem:
                if ticket_uid in to_redeem:
                     to_redeem.remove(ticket_uid)
                     ticket_booking.attrs['to_redeem'] = to_redeem
                     ticket_booking.attrs['redeemed'].append(ticket_uid)
                     ticket_state = 'redeemed'

        elif transaction == "renew":
            redeemed = ticket_booking.attrs.get('redeemed', '')
            if redeemed:
                if ticket_uid in redeemed:
                     redeemed.remove(ticket_uid)
                     ticket_booking.attrs['redeemed'] = redeemed
                     ticket_booking.attrs['to_redeem'].append(ticket_uid)
                     ticket_state = 'new'
        else:
            print "Other transaction"

        return ticket_state


    def __call__(self):
        transition = self.request['transition']
        booking_uid = self.request['uid']
        ticket_uid = self.request['ticket_uid']
        order_uid = self.request['order_uid']
        # Get booking by uid

        ticket_booking = None
        order = OrderData(self.context, uid=order_uid)
        bookings = order.bookings

        for booking in bookings:
            if str(booking.attrs['uid']) == booking_uid:
                ticket_booking = booking
                break

        #print "Ticket UID transition.\nTransition: %s\nBooking UID: %s\nTicket UID: %s\nOrder UID: %s" %(transition, str(booking_uid), str(ticket_uid), str(order_uid))

        ticket_state = self.do_ticket_transaction(transition, ticket_uid, ticket_booking)        
        return self.dropdown(self.context, self.request, ticket_booking, ticket_state, ticket_uid).render()


class RedeemStateTransition(RedeemTransition):
    dropdown = RedeemStateDropdown

class RedeemTable(RedeemTableBase):
  
    def render_filter(self):
        value = ""
        return value

    def render_order_actions_head(self):
        tag = Tag(Translate(self.request))
        select_all_orders_attrs = {
            'name': 'select_all_orders',
            'type': 'checkbox',
            'class_': 'select_all_orders',
            'title': _('select_all_orders',
                       default=u'Select all visible orders'),
        }
        select_all_orders = tag('input', **select_all_orders_attrs)
        notify_customers_target = self.context.absolute_url()
        notify_customers_attributes = {
            'ajax:target': notify_customers_target,
            'class_': 'notify_customers',
            'href': '',
            'title': _('notify_customers',
                       default=u'Notify customers of selected orders'),
        }
        notify_customers = tag('a', '&nbsp', **notify_customers_attributes)
        return select_all_orders + notify_customers

    def render_order_actions(self, colname, record):
        order_uid = record.attrs['order_uid']

        tag = Tag(Translate(self.request))
        vendor_uid = self.request.form.get('vendor', '')
        if vendor_uid:
            view_order_target = '%s?uid=%s&vendor=%s' % (
                self.context.absolute_url(),
                str(order_uid),
                vendor_uid)
        else:
            view_order_target = '%s?uid=%s' % (
                self.context.absolute_url(),
                str(order_uid))
        view_order_attrs = {
            'ajax:bind': 'click',
            'ajax:target': view_order_target,
            'ajax:overlay': 'order',
            'class_': 'contenttype-document',
            'href': '',
            'title': _('view_order', default=u'View Order'),
        }
        view_order = tag('a', '&nbsp', **view_order_attrs)
        select_order_attrs = {
            'name': 'select_order',
            'type': 'checkbox',
            'value': order_uid,
            'class_': 'select_order',
        }
        select_order = tag('input', **select_order_attrs)

        site = plone.api.portal.get()
        portal_url = site.absolute_url()

        ## Custom print order 
        data = OrderData(self.context, uid=order_uid)

        ordernumber = data.order.attrs.get('ordernumber', '')
        email = data.order.attrs.get('personal_data.email', '')

        print_order_attrs = {
            "class_": "contenttype-document",
            "href": "%s/showorder?ordernumber=%s&email=%s" %(portal_url, ordernumber, email),
            "target": "_blank",
            "title": _('view_order', default=u'View Order'),
        }

        print_order = tag('a', '&nbsp', **print_order_attrs)

        return select_order + print_order

    def check_modify_order(self, order):
        vendor_uid = self.request.form.get('vendor', '')
        if vendor_uid:
            vendor_uids = [vendor_uid]
            vendor = get_vendor_by_uid(self.context, vendor_uid)
            user = plone.api.user.get_current()
            if not user.checkPermission(permissions.ModifyOrders, vendor):
                return False
        else:
            vendor_uids = get_vendor_uids_for()
            if not vendor_uids:
                return False
        return True

    def render_salaried(self, colname, record):
        value = ""
        return value

    def render_state(self, colname, record, redeem_state, uid=None):
        return RedeemStateDropdown(self.context, self.request, record, redeem_state, uid).render()

    @property
    def ajaxurl(self):
        params = [
            ('vendor', self.request.form.get('vendor')),
            ('customer', self.request.form.get('customer'))
        ]
        query = urllib.urlencode(dict([it for it in params if it[1]]))
        query = query and '?{0}'.format(query) or ''
        site = plone.api.portal.get()

        return '%s/%s%s' % (self.context.absolute_url(), self.data_view_name, query)

    def __call__(self):
        # check if authenticated user is vendor
        if not get_vendors_for():
            raise Unauthorized
        # disable diazo theming if ajax call
        if '_' in self.request.form:
            self.request.response.setHeader('X-Theme-Disabled', 'True')
        return super(RedeemTable, self).__call__()


class TicketTableData(BrowserView):
    soup_name = None
    search_text_index = None
    total_records = 0

    @property
    def columns(self):
        """Return list of dicts with column definitions:

        [{
            'id': 'colid',
            'label': 'Col Label',
            'head': callback,
            'renderer': callback,
        }]
        """
        raise NotImplementedError(u"Abstract DataTable does not implement "
                                  u"``columns``.")

    def query(self, soup):
        """Return 2-tuple with result length and lazy record iterator.
        """
        raise NotImplementedError(u"Abstract DataTable does not implement "
                                  u"``query``.")

    def sort(self):
        columns = self.columns
        sortparams = dict()
        sortcols_idx = int(self.request.form.get('iSortCol_0'))
        sortparams['index'] = columns[sortcols_idx]['id']
        sortparams['reverse'] = self.request.form.get('sSortDir_0') == 'desc'
        return sortparams

    def all(self, soup):
        data = soup.storage.data
        sort = self.sort()
        sort_index = soup.catalog[sort['index']]
        iids = sort_index.sort(data.keys(), reverse=sort['reverse'])

        def lazyrecords():
            for iid in iids:
                yield LazyRecord(iid, soup)
        return soup.storage.length.value, lazyrecords()

    def slice(self, fullresult):
        start = int(self.request.form['iDisplayStart'])
        length = int(self.request.form['iDisplayLength'])
        count = 0
        for lr in fullresult:
            if count >= start and count < (start + length):
                yield lr
            if count >= (start + length):
                break
            count += 1

    def column_def(self, colname):
        for column in self.columns:
            if column['id'] == colname:
                return column

    def __call__(self):
        soup = get_soup(self.soup_name, self.context)
        aaData = list()
        length, lazydata = self.query(soup)
        columns = self.columns
        colnames = [_['id'] for _ in columns]

        def record2list(record, uid=None, redeemed=False):
            result = list()
            for colname in colnames:
                coldef = self.column_def(colname)
                renderer = coldef.get('renderer')
                
                if renderer:
                    ## Ticket status
                    if colname == "state":
                        redeemed_state = "new"
                        if redeemed:
                            redeemed_state = "redeemed"
                        value = renderer(colname, record, redeemed_state, uid)
                    else:
                        value = renderer(colname, record)
                else:
                    value = record.attrs.get(colname, '')

                if colname == "uid" and uid != None:
                    value = uid

                result.append(value)
            return result
        
        catalog = getToolByName(self.context, 'portal_catalog')

        self.total_records = 0
        
        for lazyrecord in self.slice(lazydata):
            booking = lazyrecord()
            count = booking.attrs['buyable_count']
            buyable_uid = booking.attrs['buyable_uid']
            ticket = False

            brains = catalog.queryCatalog({"UID": str(buyable_uid)})

            if len(brains) > 0:
                brain = brains[0]
                tags = brain.Subject
                if 'ticket' in tags:
                    ticket = True

            if ticket:
                self.total_records += 1

                for item in booking.attrs.get("redeemed", ''):
                    is_redeemed = True
                    aaData.append(record2list(booking, item, is_redeemed))

                for item in booking.attrs.get("to_redeem", ''):
                    is_redeemed = False
                    aaData.append(record2list(booking, item, is_redeemed))

        data = {
            "sEcho": int(self.request.form['sEcho']),
            #"iTotalRecords": soup.storage.length.value,
            "iTotalRecords": self.total_records,
            "iTotalDisplayRecords": length,
            "aaData": aaData,
        }

        return json.dumps(data)


class RedeemData(RedeemTable, TicketTableData):
    soup_name = 'bda_plone_orders_bookings'
    search_text_index = 'text'

    def sort(self):
        columns = self.columns
        sortparams = dict()
        sortcols_idx = int(self.request.form.get('iSortCol_0'))
        sortparams['index'] = columns[sortcols_idx]['id']
        sortparams['index'] = 'created'
        sortparams['reverse'] = self.request.form.get('sSortDir_0') == 'desc'
        return sortparams

    def _get_buyables_in_context(self):
        catalog = plone.api.portal.get_tool("portal_catalog")
        path = '/'.join(self.context.getPhysicalPath())
        brains = catalog(path=path, object_provides=IBuyable.__identifier__)
        for brain in brains:
            yield brain.UID

    def query(self, soup):
        soup.reindex()

        # fetch user vendor uids
        vendor_uids = get_vendor_uids_for()
        # filter by given vendor uid or user vendor uids
        vendor_uid = self.request.form.get('vendor')

        if vendor_uid:
            vendor_uid = uuid.UUID(vendor_uid)
            # raise if given vendor uid not in user vendor uids
            if vendor_uid not in vendor_uids:
                raise Unauthorized
            query = Any('vendor_uid', [vendor_uid])
        else:
            query = Any('vendor_uid', vendor_uids)

        # filter by customer if given
        customer = self.request.form.get('customer')
        if customer:
            query = query & Eq('creator', customer)

        query = Eq('salaried', 'yes')
        # filter by search term if given
        term = self.request.form['sSearch'].decode('utf-8')

        if term:
            query = query & Contains(self.search_text_index, term)

        # Show only tickets that are paid
        

        if not ISiteRoot.providedBy(self.context):
            buyable_uids = self._get_buyables_in_context()
            b_uids = list(buyable_uids)
            query = query & Any('buyable_uid', b_uids)

        # query orders and return result
        sort = self.sort()
        try:
            res = soup.lazy(query,
                          sort_index=sort['index'],
                          reverse=sort['reverse'],
                          with_size=True)

            length = res.next()
        except:
            length = 0
            pass

        return length, res

    def query2(self, soup):

        # fetch user vendor uids
        vendor_uids = get_vendor_uids_for()
        # filter by given vendor uid or user vendor uids
        vendor_uid = self.request.form.get('vendor')

        if vendor_uid:
            vendor_uid = uuid.UUID(vendor_uid)
            # raise if given vendor uid not in user vendor uids
            if vendor_uid not in vendor_uids:
                raise Unauthorized
            query = Any('vendor_uids', [vendor_uid])
        else:
            query = Any('vendor_uids', vendor_uids)
        # filter by customer if given
        customer = self.request.form.get('customer')
        if customer:
            query = query & Eq('creator', customer)
        # filter by search term if given
        term = self.request.form['sSearch'].decode('utf-8')
        if term:
            query = query & Contains(self.search_text_index, term)
        # query orders and return result
        sort = self.sort()
        res = soup.lazy(query,
                      sort_index=sort['index'],
                      reverse=sort['reverse'],
                      with_size=True)
        length = res.next()


        return length, res


###
### Tickets view
###
class TicketView(CartView):
    def get_qr_code(self, ticket_uid):
        request = "https://chart.googleapis.com/chart?chs=150x150&cht=qr&chl=%s&chld=L|1&choe=UTF-8" %(ticket_uid)
        return request

    def get_tickets(self):
        return self.data_provider.data["cart_items"]

    def toLocalizedTime(self, time, long_format=None, time_only=None):
        """Convert time to localized time
        """
        context = aq_inner(self.context)
        util = getToolByName(context, 'translation_service')
        return util.ulocalized_time(time, long_format, time_only,
                                    context=context, domain='plonelocales',
                                    request=self.request)

    def get_etickets(self, order_id):
        tickets = {
          "tickets": [],
          "customer": "",
          "total_tickets": 0
        }

        
        try:
            data = OrderData(self.context, uid=order_id)
            bookings = data.bookings
            total_items = 0

            first_name = data.order.attrs['personal_data.firstname']
            last_name =  data.order.attrs['personal_data.lastname']
            created_date = data.order.attrs['created']
            b_uids = data.order.attrs['buyable_uids']
            customer_name = "%s %s" %(first_name, last_name)
            tickets['customer'] = customer_name
            #tickets['is_event'] = False
            tickets['event_date'] = ""
            """if b_uids:
                b_uid = b_uids[0]
                b_obj = uuidToObject(b_uid)
                b_parent = b_obj.aq_parent
                if b_parent.portal_type == "Event":
                    tickets["is_event"] = True
                    start_date = b_parent.start_date.date()
                    end_date = b_parent.end_date.date()
                    formatted_date = ""
                    if start_date == end_date:
                        formatted_date = "%s, %s - %s" %(self.toLocalizedTime(b_parent.start_date.strftime('%d %B %Y')), self.toLocalizedTime(b_parent.start_date, time_only=1), self.toLocalizedTime(b_parent.end_date, time_only=1))
                    else:
                        formatted_date = "%s - %s" %(self.toLocalizedTime(b_parent.start_date.strftime('%d %B %Y')), self.toLocalizedTime(b_parent.end_date.strftime('%d %B %Y')))
                    tickets["event_date"] = formatted_date"""
            
            for booking in bookings:
                # Check if booking is an event
                is_event = False
                buyable_uid = booking.attrs['buyable_uid']
                b_brain = uuidToCatalogBrain(buyable_uid)
                if "event" in b_brain.Subject:
                    is_event = True

                original_price = (Decimal(str(booking.attrs['net']))) * 1
                price_total = original_price + original_price / Decimal(100) * Decimal(str(booking.attrs['vat']))

                total_items += booking.attrs['buyable_count']

                tickets['tickets'].append({
                  "cart_item_title": booking.attrs['title'],
                  "cart_item_price": ascur(price_total),
                  "cart_item_count": len(booking.attrs['to_redeem']),
                  "booking_uid": booking.attrs['uid'],
                  "cart_item_original_price": "",
                  "order_created_date": created_date,
                  "to_redeem": booking.attrs['to_redeem'],
                  "is_event": is_event
                })

                tickets["total_tickets"] = total_items
        except:
            raise
            return tickets
        
        return tickets


