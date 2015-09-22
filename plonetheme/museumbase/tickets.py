#!/usr/bin/env python
# -*- coding: utf-8 -*

from decimal import Decimal

def find_context(request):
    published = request.get('PUBLISHED', None)
    context = getattr(published, '__parent__', None)
    if context is None:
        context = request.PARENTS[0]
    return context

def find_tickets(context):
    catalog = context.portal_catalog
    path = "/NewTeylers/%s/tickets" %(context.language)
    brains = catalog(path={'query': path, 'depth': 1}, portal_type='product', sort_on='getObjPositionInParent')
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

        if '/tickets' in context.absolute_url():
            ret = add_tickets(ret, context)
        else:
            ret = remove_tickets(ret, context)

    return ret



