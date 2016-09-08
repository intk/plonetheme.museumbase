#!/usr/bin/env python
# -*- coding: utf-8 -*

from decimal import Decimal

ALLOWED_TYPES_TICKETS = ['Event']

def is_ticket(context):
    if context:
        if "/tickets" in context.absolute_url():
            return True

        if context.portal_type in ALLOWED_TYPES_TICKETS:
            physical_path = context.getPhysicalPath()
            path = "/".join(physical_path)

            results = context.portal_catalog(path={'query': path, 'depth': 1}, portal_type="product", Subject="ticket")
            if len(results) > 0:
                return True

        return False
    else:
        return False

def find_context(request):
    published = request.get('PUBLISHED', None)
    context = getattr(published, '__parent__', None)
    if context is None:
        context = request.PARENTS[0]
    return context

def find_tickets(context):
    catalog = context.portal_catalog
    physical_path = context.getPhysicalPath()
    path = "/".join(physical_path)
    brains = catalog(path={'query': path, 'depth': 1}, portal_type='product', sort_on='getObjPositionInParent', Subject="ticket")
    return brains

def add_tickets(ret, context):
    tickets = find_tickets(context)

    # Populate ticket ids
    uids = []
    for ticket in tickets:
        uids.append((ticket.UID, Decimal(0), ''))
    
    for uid, count, comment in ret:
        for index, elem in enumerate(uids):
            if elem[0] == uid:
                uids[index] = (uid, Decimal(count), comment)
                break

    return uids

def remove_tickets(ret, context):
    tickets = find_tickets(context)

    uuids = []
    for ticket in tickets:
        uuids.append(ticket.UID)

    new_ret = []

    for item in ret:
        if item[0] not in uuids:
            new_ret.append(item)

    return new_ret

def extractTickets(ret, request):
    if request != None:
        context = find_context(request)

        if is_ticket(context):
            ret = add_tickets(ret, context)
        else:
            ret = remove_tickets(ret, context)

    return ret



