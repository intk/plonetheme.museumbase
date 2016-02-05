#!/usr/bin/python
# -*- coding: utf-8 -*-

from Products.Five import BrowserView
import json
from zope.component import getMultiAdapter
from Products.CMFCore.utils import getToolByName
from collective.leadmedia.interfaces import ICanContainMedia
from zope.schema import getFieldsInOrder
from Products.mediaObject.object import IObject
from plone.dexterity.interfaces import IDexterityFTI
from zope.component import getUtility
from Products.CMFCore.utils import getToolByName
from zope.i18nmessageid import MessageFactory
from plone.app.uuid.utils import uuidToCatalogBrain, uuidToObject
from plone.app.contenttypes.interfaces import ICollection
import re

MessageFactory = MessageFactory('Products.mediaObject')
NOT_ALLOWED = [None, '', ' ', []]

class get_nav_objects(BrowserView):
    """
    Utils
    """
    def get_slideshow_items(self):
        item = self.context
        order = self.request.get('sort_on')
        catalog = getToolByName(self.context, 'portal_catalog')

        scale = "/@@images/image/large"

        items = []

        if item.portal_type == "Object":
            if hasattr(item, 'slideshow'):
                slideshow = item['slideshow']
                path = '/'.join(slideshow.getPhysicalPath())

                if order == None:
                    order = 'getObjPositionInParent'

                results = catalog.searchResults(path={'query': path, 'depth': 1}, sort_on=order)
                for brain in results:
                    url = brain.getObject().absolute_url()
                    slideshow_url = "%s%s" %(url, scale)
                    items.append({'url':slideshow_url})

        return json.dumps(items)


    def get_object_idx(self, results, object_id, is_folder):
        if is_folder:
            for idx, res in enumerate(results):
                if res.getId == object_id:
                    return idx
        else:
            for idx, res in enumerate(results):
                if res.getId() == object_id:
                    return idx

    def get_all_batch(self, collection_object, is_folder):
        catalog = getToolByName(self.context, 'portal_catalog')

        if is_folder:
            collection_obj = collection_object
        else:
            collection_obj = collection_object.getObject()
        if is_folder:
            folder_path = '/'.join(collection_obj.getPhysicalPath())
            results = catalog(path={'query': folder_path, 'depth': 1, 'portal_type':'Object'})
        else:
            results = collection_obj.queryCatalog(batch=False)
        return results

    def get_batch(self, collection_object, start, pagesize=33):
        collection_obj = collection_object.getObject()
        results = collection_obj.queryCatalog(batch=True, b_start=int(start), b_size=pagesize)
        return results

    """
    Get prev obj
    """
    def get_prev_obj(self, start, collection_id):
        pagesize = 33
        
        if "/" not in start:
            object_id = self.context.getId()
            collection_object = uuidToCatalogBrain(collection_id)

            if collection_object:
                if collection_object.portal_type == "Collection":
                    ## Get Batch of collection
                    results = self.get_batch(collection_object, start, pagesize)
                    
                    ## Get prev item
                    object_idx = self.get_object_idx(results, object_id)                    
                    if object_idx > 0:
                        return results[object_idx-1]
                    else:
                        if results.has_previous:
                            page = results.previouspage
                            start = int(start)
                            start = (page * pagesize) - pagesize
                            b_results = self.get_batch(collection_object, start, pagesize)
                            last_element = b_results[b_results.items_on_page-1]
                            return last_element
                        else:
                            lastpage = results.lastpage
                            start = int(start)
                            start = (lastpage * pagesize) - pagesize
                            b_results = self.get_batch(collection_object, start, pagesize)
                            last_element = b_results[b_results.items_on_page-1]
                            return last_element
    """
    Get next obj
    """
    def get_next_obj(self, start, collection_id):
        pagesize = 33

        if "/" not in start:
            object_id = self.context.getId()
            collection_object = uuidToCatalogBrain(collection_id)

            if collection_object:
                if collection_object.portal_type == "Collection":
                    results = self.get_batch(collection_object, start, pagesize)
                    object_idx = self.get_object_idx(results, object_id)
                    if object_idx < results.items_on_page-1:
                        return results[object_idx+1]
                    else:
                        if results.has_next:
                            page = results.nextpage
                            page -= 1
                            start = int(start)
                            start = (page * pagesize)
                            b_results = self.get_batch(collection_object, start, pagesize)
                            first_element = b_results[0]
                            return first_element
                        else:
                            start = 0
                            b_results = self.get_batch(collection_object, start, pagesize)
                            first_element = b_results[0]
                            return first_element

    def get_collection_from_catalog(self, collection_id):
        uuid = collection_id
        collection_object = uuidToCatalogBrain(collection_id)
        if collection_object:
            if collection_object.portal_type == "Collection":
                return collection_object

        return None

    def get_all_items_from_collection(self, collection_object):
        items = {
            "list":[],
            "object_idx":0,
            'total':False
        }

        results = self.get_all_batch(collection_object, False)
        object_idx = self.get_object_idx(results, self.context.getId())
        items['object_idx'] = object_idx

        for obj in results:
            if obj != None:
                obj_media = ICanContainMedia(obj.getObject()).getLeadMedia()
                if obj_media != None:
                    items['list'].append({'url':obj.getURL(),'image_url': obj_media.absolute_url()+'/@@images/image/large', 'object_id': obj.getId(), 'title':obj.Title(), 'description': obj.Description(), 'body': ""})

        return items

    """
    AJAX to get all items inside collection
    """
    def get_all_collection(self):
        collection_id = self.request.get('collection_id')
        items = []
        
        if collection_id != None:
            collection_object = self.get_collection_from_catalog(collection_id)
            if collection_object != None:
                ## Get Batch of collection
                items = self.get_all_items_from_collection(collection_object)

        return json.dumps(items)

    def get_multiple_images(self, _object, view_type):
        images = []
        
        if view_type == 'double_view':
            limit = 2
            curr = 0
            if hasattr(_object, 'slideshow'):
                slideshow = _object['slideshow']
                if slideshow.portal_type == "Folder":
                    for img in slideshow:
                        curr += 1 
                        if slideshow[img].portal_type == 'Image':
                            images.append(slideshow[img].absolute_url()+'/@@images/image/large')
                        if curr >= limit:
                            break

        elif view_type == 'multiple_view':
            if hasattr(_object, 'slideshow'):
                slideshow = _object['slideshow']
                if slideshow.portal_type == "Folder":
                    for img in slideshow:
                        if slideshow[img].portal_type == 'Image':
                            images.append(slideshow[img].absolute_url()+'/@@images/image/large')

        res = sorted(images)
        return res

    def trim_white_spaces(self, text):
        if text != "" and text != None:
            if len(text) > 0:
                if text[0] == " ":
                    text = text[1:]
                if len(text) > 0:
                    if text[-1] == " ":
                        text = text[:-1]
                return text
            else:
                return ""
        else:
            return ""

    def create_author_name(self, value):
        
        final_author = ""

        author_name = value
        brackets_content = re.findall('\(.*?\)',value)
        for b in brackets_content:
            author_name = author_name.replace(b, '')
            author_name = author_name.strip()

        split_name = author_name.split(',')
        if len(split_name) > 2:
            final_value = '<a href="/'+self.context.language+'/search?SearchableText=%s">%s</a>' %(value, value)
            return final_value

        new_author = []
        if len(split_name) > 1 and len(split_name) > 0:
            new_author.append(split_name[-1])
            new_author.append(split_name[0])
        elif len(split_name) > 0:
            new_author.append(split_name[0])
        else:
            new_author.append(value)

        final_author_name = " ".join(new_author)
        final_author_name = '<a href="/'+self.context.language+'/search?SearchableText=%s">%s</a>' %(final_author_name, final_author_name)

        final_brackets = []
        final_brackets.append(final_author_name)
        final_brackets.extend(brackets_content)

        final_value = " ".join(final_brackets)

        return final_value

    def create_materials(self, value):
        materials = value.split(',')
        _value = ""
        for i, mat in enumerate(materials):
            if i == (len(materials)-1):
                _value += '<a href="/'+self.context.language+'/search?SearchableText=%s">%s</a>' % (mat.replace('"', "'"), mat)
            else:
                _value += '<a href="/'+self.context.language+'/search?SearchableText=%s">%s</a>, ' % (mat.replace('"', "'"), mat)

        return _value

    def create_production_field(self, field):

        authors = []
        
        for author in field:
            production = ""

            maker = author['creator']
            qualifier = author['qualifier']
            role = author['role']
            date_of_birth = author['date_of_birth']
            date_of_death = author['date_of_death']

            if maker not in NOT_ALLOWED:
                production = '<a href="/'+self.context.language+'/search?SearchableText=%s">%s</a>' % (maker.replace("(-", "("), maker)

                dates = ""
                if date_of_birth not in NOT_ALLOWED:
                    dates = "%s" %(date_of_birth)
                    if date_of_death not in NOT_ALLOWED:
                        dates = "%s-%s" %(dates, date_of_death)
                elif date_of_death not in NOT_ALLOWED:
                    dates = "%s" %(date_of_death)

                if dates not in NOT_ALLOWED:
                    if production:
                        production = "%s, (%s)" %(production, dates)

                if role not in NOT_ALLOWED:
                    if production:
                        production = "%s (%s)" %(production, role)
                    else:
                        production = "(%s)" %(role)

                authors.append(production)

        final_production = "<p>".join(authors)

        return final_production

    def create_dimension_field(self, field):
        new_dimension_val = []
        dimension_result = ""

        for val in field:
            dimension = ""
            if val['value'] not in NOT_ALLOWED:
                dimension = "%s" %(val['value'])
            else:
                continue
            if val['unit'] not in NOT_ALLOWED:
                dimension = "%s %s" %(dimension, val['unit'].lower())
            if val['type'] not in NOT_ALLOWED:
                dimension = "%s: %s" %(val['type'].lower(), dimension)
            else:
                continue

            if val['part'] not in NOT_ALLOWED:
                dimension = "%s (%s)" %(dimension, val['part'])

            new_dimension_val.append(dimension)

        dimension_result = '<p>'.join(new_dimension_val)
        
        return dimension_result

    def create_general_repeatable(self, field, name):

        values = []

        if "period" in name:
            separator = "<p>"

            for line in field:
                period = line['period']
                place = ""
                reason = line['reason']
                notes = line['notes']

                if period not in NOT_ALLOWED:
                    values.append(period)

                if place not in NOT_ALLOWED:
                    values.append(place)

                if reason not in NOT_ALLOWED:
                    values.append(reason)

                if notes not in NOT_ALLOWED:
                    values.append(notes)

            final_value = separator.join(values)
            return final_value

        else:
            separator = ", "

        for line in field:
            new_line = []
            if type(line) == dict:
                for key, value in line.iteritems():
                    if value not in NOT_ALLOWED:
                        if name in ['object_material', 'object_technique']:
                            new_value = '<a href="/'+self.context.language+'/search?SearchableText=%s">%s</a>' % (value, value)
                            new_line.append(new_value)
                        else:   
                            new_line.append(value)

                final_line = separator.join(new_line)
                values.append(final_line)
            else:
                if line not in NOT_ALLOWED:
                    if name in ['object_material', 'object_technique']:
                        new_value = '<a href="/'+self.context.language+'/search?SearchableText=%s">%s</a>' % (value, value)
                        new_line.append(new_value)
                    else: 
                        values.append(line)

        final_value = "<p>".join(values)

        return final_value
        
    def create_prod_dating_field(self, field, obj):
        period = None
        start_date = field['start']
        start_date_precision = field['start_precision']
        end_date = field['end']
        end_date_precision = field['end_precision']

        if end_date == start_date:
            end_date = ""

        result = ""

        if period not in NOT_ALLOWED:
            result = "%s" %(period)

        if start_date not in NOT_ALLOWED:
            if result:
                if start_date_precision not in NOT_ALLOWED:
                    result = "%s, %s %s" %(result, start_date_precision, start_date)
                else:
                    result = "%s, %s" %(result, start_date)
            else:
                if start_date_precision not in NOT_ALLOWED:
                    result = "%s %s" %(start_date_precision, start_date)
                else:
                    result = "%s" %(start_date)
    

        if end_date not in NOT_ALLOWED:
            if result:
                if end_date_precision not in NOT_ALLOWED:
                    if end_date_precision != start_date_precision:
                        result = "%s - %s %s" %(result, end_date_precision, end_date)
                    else:
                        result = "%s - %s" %(result, end_date)
                else:
                    result = "%s - %s" %(result, end_date)
            else:
                if end_date_precision not in NOT_ALLOWED:
                    result = "%s %s" %(end_date_precision, end_date)
                else:
                    result = "%s" %(end_date)

        object_period = getattr(obj, 'object_production_period', "")
        if object_period:
            if object_period[0]['period'] == result:
                return ""

        return result



    def create_production_dating_field(self, period_field, obj):
        period = []
        for field in period_field:
            result = self.create_prod_dating_field(field, obj)
            if result not in NOT_ALLOWED:
                period.append(result)

        final_period = "<p>".join(period)
        return final_period

    def create_inscription_field(self, field):
        inscriptions = []

        for line in field:
            _type = line["type"]
            _content = line["content"]

            if _type not in NOT_ALLOWED and _content not in NOT_ALLOWED:
                new_line = "%s: %s" %(_type, _content)
                inscriptions.append(new_line)
            elif _content not in NOT_ALLOWED:
                new_line = "%s" %(_content)
                inscriptions.append(new_line)

        if inscriptions:
            final_inscriptions = "<p>".join(inscriptions)
            return final_inscriptions
        else:
            return ""

    def create_digital_ref_field(self, field):

        refs = []

        for line in field:
            ref = line['reference']
            title = line['description']

            if title not in NOT_ALLOWED and ref not in NOT_ALLOWED:
                new_ref = '<a href="%s" target="_blank">%s</a>' % (ref, title)
                refs.append(new_ref)
            elif title not in NOT_ALLOWED:
                new_ref = title
                refs.append(new_ref)
            elif ref not in NOT_ALLOWED:
                new_ref = '<a href="%s" target="_blank">%s</a>' % (ref, ref)
                refs.append(new_ref)
            else:
                pass

        if refs:
            final_refs = "<p>".join(refs)
            return final_refs
        else:
            return ""

    def create_period_field(self, field, obj, name):

        title = "Period"

        object_dating = getattr(obj, 'object_dating', "")
        value = ""

        if object_dating:
            for line in object_dating:
                if line['start'] not in NOT_ALLOWED:
                    if line['end'] not in NOT_ALLOWED:
                        if line['start'] == line['end']:
                            value = line['start']
                            break

        if field and value:
            if field[0]['period'] == value:
                title = "Dating"

        result = self.create_general_repeatable(field, name)

        return result, title

    def create_production_place(self, field, obj, name):
        values = []
        separator = "<p>"

        for line in field:
            place = line['place']
            if place not in NOT_ALLOWED:
                values.append(place)

        final_value = separator.join(values)
        return final_value


    def get_all_fields_object(self, object):
        object_schema = []
        schema = getUtility(IDexterityFTI, name='Object').lookupSchema()

        state = getMultiAdapter(
                (self.context, self.request),
                name=u'plone_context_state')

        # Check view type
        view_type = state.view_template_id()

        if object.portal_type == 'Object':
            for name, field in getFieldsInOrder(schema):
                if name not in ["text", "object_tags", "book_title", "priref", "administration_name", "object_reproduction_reference", "stable_uri"]:
                    value = getattr(object, name, '')

                    if type(value) == list:
                        if "creator" in name or 'object_author' in name:
                            value = self.create_production_field(value)
                            if value:
                                _title = MessageFactory(field.title)
                                
                                if view_type == "double_view":
                                    _title = MessageFactory("People/event(s) involved")

                                new_attr = {"title": self.context.translate(_title), "value": value, "name": name}
                                object_schema.append(new_attr)
                        elif "dimension" in name:
                            value = self.create_dimension_field(value)
                            if value:
                                _title = MessageFactory(field.title)
                                new_attr = {"title": self.context.translate(_title), "value": value, "name": name}
                                object_schema.append(new_attr)

                        elif "dating" in name:
                            value = self.create_production_dating_field(value, object)
                            if value:
                                _title = MessageFactory(field.title)
                                new_attr = {"title": self.context.translate(_title), "value": value, "name": name}
                                object_schema.append(new_attr)

                        elif "inscription" in name:
                            value = self.create_inscription_field(value)
                            if value:
                                _title = MessageFactory(field.title)
                                new_attr = {"title": self.context.translate(_title), "value": value, "name": name}
                                object_schema.append(new_attr)

                        elif "digital_reference" in name:
                            value = self.create_digital_ref_field(value)
                            if value:
                                _title = MessageFactory(field.title)
                                new_attr = {"title": self.context.translate(_title), "value": value, "name": name}
                                object_schema.append(new_attr)

                        elif "object_production_period" in name:
                            final_value, title = self.create_period_field(value, object, name)
                            if final_value:
                                _title = MessageFactory(title)
                                new_attr = {"title": self.context.translate(_title), "value": final_value, "name": name}
                                object_schema.append(new_attr)

                            final_value = self.create_production_place(value, object, name)
                            if final_value:
                                _title = MessageFactory("Place of production")
                                new_attr = {"title": self.context.translate(_title), "value": final_value, "name": name}
                                object_schema.append(new_attr)
                                
                        else:
                            value = self.create_general_repeatable(value, name)
                            if value:
                                _title = MessageFactory(field.title)
                                new_attr = {"title": self.context.translate(_title), "value": value, "name": name}
                                object_schema.append(new_attr)

                    
                    else:
                        value = self.trim_white_spaces(value)
                        if name in ["object_title", "translated_title"]:
                            if "fossielen" in object.absolute_url():
                                value = ""

                        if value not in NOT_ALLOWED:
                            if name in ['technique', 'artist', 'material', 'object_type', 'object_category', 'publisher', 'author']:
                                if name in ['artist', 'author']:
                                    _value = self.create_author_name(value)
                                    value = _value
                                elif name in ['material', 'technique']:
                                    _value = self.create_materials(value)
                                    value = _value
                                else:
                                    _value = '<a href="/'+self.context.language+'/search?SearchableText=%s">%s</a>' % (value, value)
                                    value = _value

                            _title = MessageFactory(field.title)
                            new_attr = {"title": self.context.translate(_title), "value": value, "name": name}
                            
                            if name in ['artist', 'author']:
                                object_schema.insert(0, new_attr)
                            else:
                                object_schema.append(new_attr)
            
            ##object_title = getattr(object, 'title', '')
            ##new_attr = {'title': self.context.translate('Title'), "value": object_title}

            """if len(object_schema) > 1 and object_schema[0]['name'] == "author":
                if object_schema[1]['name'] == "illustrator":
                    if object.book_title != '':
                        new_attr = {'title': self.context.translate('Title'), "value": object.book_title}
                        object_schema.insert(2, new_attr)
                else:
                    if object.book_title != '':
                        new_attr = {'title': self.context.translate('Title'), "value": object.book_title}
                        object_schema.insert(1, new_attr)

            if len(object_schema) > 1 and object_schema[0]['name'] == "artist":
                object_schema.insert(1, new_attr)
            elif len(object_schema) > 1 and object_schema[0]['name'] != "artist" and object_schema[0]['name'] != "author":
                object_schema.insert(0, new_attr)"""

            obj_body = self.get_object_body(object)
            object_schema.append({"title": "body", "value":obj_body})
        else:
            object_schema = []

        return object_schema

    def build_json_with_list(self, list_items, object_idx, total, is_folder, total_items):
        items = {
            'list':[],
            'object_idx':object_idx,
            'total': total,
            'has_list_images':False,
            'view_type': 'regular',
            'total_items': 0
        }

        state = getMultiAdapter(
                (self.context, self.request),
                name=u'plone_context_state')

        # Check view type
        view_type = state.view_template_id()

        if view_type == "double_view" or view_type == "multiple_view":
            items["has_list_images"] = True
            items["view_type"] = view_type

        items['total_items'] = total_items

        if is_folder:
            for obj in list_items:
                obj_media = ICanContainMedia(obj.getObject()).getLeadMedia()
                if obj_media != None:
                    schema = self.get_all_fields_object(obj.getObject())
                    if not items['has_list_images']:
                        items['list'].append({'schema':schema, 'url':obj.getURL(),'image_url': obj_media.absolute_url()+'/@@images/image/large', 'object_id': obj.getId, 'title':obj.Title, 'description': obj.Description, 'body': self.get_object_body(obj.getObject())})
                    else:
                        items['list'].append({'schema':schema, 'images':self.get_multiple_images(obj.getObject(), view_type), 'url':obj.getURL(),'image_url': obj_media.absolute_url()+'/@@images/image/large', 'object_id': obj.getId, 'title':obj.Title, 'description': obj.Description, 'body': self.get_object_body(obj.getObject())})              
        else:
            for obj in list_items:
                obj_media = ICanContainMedia(obj.getObject()).getLeadMedia()
                if obj_media != None:
                    schema = self.get_all_fields_object(obj.getObject())
                    if not items['has_list_images']:
                        items['list'].append({'schema':schema, 'url':obj.getURL(),'image_url': obj_media.absolute_url()+'/@@images/image/large', 'object_id': obj.getId(), 'title':obj.Title(), 'description': obj.Description(), 'body': self.get_object_body(obj)})
                    else:
                        items['list'].append({'schema':schema, 'images':self.get_multiple_images(obj.getObject(), view_type), 'url':obj.getURL(),'image_url': obj_media.absolute_url()+'/@@images/image/large', 'object_id': obj.getId(), 'title':obj.Title(), 'description': obj.Description(), 'body': self.get_object_body(obj)})                
        return items

    """
    Get bulk of prev items
    """
    def get_prev_objects(self):
        bulk = 30
        b_start = self.request.get('b_start')
        collection_id = self.request.get('collection_id')
        object_id = self.request.get('object_id')

        if b_start != None and collection_id != None and object_id != None:
            collection_object = self.get_collection_from_catalog(collection_id)
            results = self.get_all_batch(collection_object, False)
            object_idx = self.get_object_idx(results, object_id)

            if object_idx-bulk >= 0:
                list_of_items = list(results)
                bulk_of_items = list_of_items[(object_idx-bulk):object_idx]
                items = self.build_json_with_list(bulk_of_items, 0, False, False, len(list_of_items))
                items['list'] = list(reversed(items['list']))
                return json.dumps(items)

        return json.dumps({'list':[], 'object_idx':0})

    """
    Get bulk of next items
    """
    def get_next_objects(self):
        bulk = 30
        b_start = self.request.get('b_start')
        collection_id = self.request.get('collection_id')
        object_id = self.request.get('object_id')
        req_bulk = self.request.get('bulk')

        if req_bulk != None:
            buffer_size = int(req_bulk)

        is_collection = False
        is_folder = False
        if b_start != None and collection_id != None:
            is_collection = True
        else:
            if self.context.getParentNode() != None:
                parent = self.context.getParentNode();
                if parent.portal_type == 'Folder':
                    is_folder = True

        if not (is_folder == False and is_collection == False) and object_id != None:
            if is_collection:
                collection_object = self.get_collection_from_catalog(collection_id)
            else:
                collection_object = parent

            results = self.get_all_batch(collection_object, is_folder)
            object_idx = self.get_object_idx(results, object_id, is_folder)

            if object_idx+bulk < len(results):
                list_of_items = list(results)
                bulk_of_items = list_of_items[(object_idx+1):(object_idx+bulk+1)]
                items = self.build_json_with_list(bulk_of_items, 0, False, is_folder, len(list_of_items))
                return json.dumps(items)
            
            elif object_idx+bulk >= len(results):
                list_of_items = list(results)
                offset = (object_idx+bulk) - len(results)
                bulk_of_items = list_of_items[(object_idx+1):] + list_of_items[0:(offset+1)]
                items = self.build_json_with_list(bulk_of_items, 0, True, is_folder, len(list_of_items))
                return json.dumps(items)

        return json.dumps({'list':[], 'object_idx':0, 'total':False})

    def get_object_body(self, object):
        if hasattr(object, 'text') and object.text != None:
            try:
                return object.text.output
            except:
                return ""
        else:
            return ""

    def _get_next_objects(self):
        buffer_size = 10
        b_start = self.request.get('b_start')
        collection_id = self.request.get('collection_id')
        object_id = self.request.get('object_id')
        req_bulk = self.request.get('bulk')

        dangerous_entries = int(object_id)

        collection_object = uuidToObject(collection_id)

        if collection_object.portal_type == "Collection":
            new_start = dangerous_entries

            if int(b_start) > buffer_size:
                new_start = int(b_start) + 5
            
            sort_on = ICollection(collection_object).sort_on
            next_batch = collection_object.queryCatalog(batch=True, b_size=buffer_size, b_start=new_start+1, sort_on=sort_on)
            next_items = next_batch._sequence

            collection_total_size = next_items.actual_result_count
            items = self.build_json_with_list(next_items, 0, False, False, collection_total_size)
            return json.dumps(items)

        return json.dumps({'list':[], 'object_idx':0, 'total':False})

    def _getJSON(self):
        buffer_size = 10

        object_id = self.context.getId()

        b_start = self.request.get('b_start')
        b_start = int(b_start)
        collection_id = self.request.get('collection_id')
        req_buffer = self.request.get('bulk')
        #if req_buffer:
        #    buffer_size = int(req_buffer)

        collection_object = uuidToObject(collection_id)

        if collection_object.portal_type == "Collection":
            b_size = ICollection(collection_object).item_count
            sort_on = ICollection(collection_object).sort_on
            real_object_index = b_start

            if real_object_index - buffer_size < 0:
                new_size = buffer_size - abs(real_object_index-buffer_size)
                if new_size:
                    prev_batch = collection_object.queryCatalog(batch=True, b_size=new_size, b_start=0, sort_on=sort_on)
                    prev_items = prev_batch._sequence
                else:
                    prev_items = []

            elif real_object_index - buffer_size >= 0:
                new_start = real_object_index - buffer_size
                if buffer_size:
                    prev_batch = collection_object.queryCatalog(batch=True, b_size=buffer_size, b_start=new_start, sort_on=sort_on)
                    prev_items = prev_batch._sequence
                else:
                    prev_items = []

            next_batch = collection_object.queryCatalog(batch=True, b_size=buffer_size, b_start=real_object_index, sort_on=sort_on)
            next_items = next_batch._sequence

            collection_total_size = next_items.actual_result_count
            final_items = list(next_items) + list(prev_items)
            items = self.build_json_with_list(final_items, 0, False, False, collection_total_size)
            items['index_obj'] = real_object_index+1

            return json.dumps(items)

        return json.dumps({'list':[], 'object_idx':0, 'total':False})

    def getJSON(self):
        pagesize = 33
        
        buffer_size = 30
        b_start = self.request.get('b_start')
        collection_id = self.request.get('collection_id')
        req_bulk = self.request.get('bulk')

        if req_bulk != None:
            buffer_size = int(req_bulk)

        items = {}

        is_folder = False
        is_collection = False

        if b_start != None and collection_id != None:
            is_collection = True
        else:
            if self.context.getParentNode() != None:
                parent = self.context.getParentNode();
                if parent.portal_type == 'Folder':
                    is_folder = True

        if not (is_folder == False and is_collection == False): 
            if is_collection:
                collection_object = self.get_collection_from_catalog(collection_id)
            else:
                collection_object = parent

            current_id = self.context.getId()

            results = self.get_all_batch(collection_object, is_folder)
            object_idx = self.get_object_idx(results, current_id, is_folder)

            if object_idx-buffer_size >= 0 and object_idx+buffer_size < len(results):
                list_of_items = list(results)
                
                prev_items = list_of_items[(object_idx-buffer_size):object_idx]
                next_items = list_of_items[object_idx:(object_idx+buffer_size+1)]

                bulk_of_items = next_items + prev_items
                
                items = self.build_json_with_list(bulk_of_items, 0, False, is_folder, len(list_of_items))
                items['index_obj'] = object_idx+1
                return json.dumps(items)
            
            elif object_idx-buffer_size < 0 and object_idx+buffer_size < len(results):
                #fetch from last page
                offset = object_idx-buffer_size
                
                list_of_items = list(results)
                prev_items = list_of_items[offset:] + list_of_items[0:object_idx]
                next_items = list_of_items[object_idx:(object_idx+buffer_size+1)]

                bulk_of_items = next_items + prev_items
                
                items = self.build_json_with_list(bulk_of_items, 0, False, is_folder, len(list_of_items))
                items['index_obj'] = object_idx+1
                return json.dumps(items)

            elif object_idx+buffer_size >= len(results) and object_idx-buffer_size > 0:
                list_of_items = list(results)

                offset = (object_idx+buffer_size) - len(results)

                prev_items = list_of_items[(object_idx-buffer_size):object_idx]
                next_items = list_of_items[object_idx:] + list_of_items[0:(offset+1)]

                bulk_of_items = next_items + prev_items
                items = self.build_json_with_list(bulk_of_items, 0, False, is_folder, len(list_of_items))
                items['index_obj'] = object_idx+1
                return json.dumps(items)

            elif object_idx+buffer_size >= len(results) and object_idx-buffer_size < 0:
                list_of_items = list(results)

                prev_items = list_of_items[0:object_idx]
                next_items = list_of_items[object_idx:]

                bulk_of_items = next_items + prev_items
                items = self.build_json_with_list(bulk_of_items, 0, True, is_folder, len(list_of_items))
                items['index_obj'] = object_idx+1
                return json.dumps(items)
        else:
            return json.dumps(items);


class get_slideshow_options(BrowserView):
    """
    AJAX call to get slideshow options
    """
    def getJSON(self):
        callback = hasattr(self.request, 'callback') and 'json' + self.request['callback'] or None
        only_documented = not hasattr(self.request, 'only_documented') 
        
        state = getMultiAdapter(
                (self.context, self.request),
                name=u'plone_context_state')

        # Check view type
        view_type = state.view_template_id()

        if view_type == "double_view":
            options = {
                'changes': True,
                'slidesToShow': 2,
                'arrows':False,
                'height':'480px',
                'type': 'double'
            }
        elif view_type == "multiple_view":
            options = {
                'changes': True,
                'autoplay': True,
                'autoplaySpeed': 500,
                'type': 'multiple',
                'arrows': False
            }
        else:
            options = {
                'changes': False
            }

        json_str = json.dumps(options)

        if callback is not None:
            return callback +'(' + json_str + ')'
        else:
            return json_str


class get_fields(BrowserView):
    """
    Utils
    """

    def get_object_body(self, object):
        if hasattr(object, 'text') and object.text != None:
            try:
                return object.text.output
            except:
                return ""
        else:
            return ""

    def trim_white_spaces(self, text):
        if text != "" and text != None:
            if len(text) > 0:
                if text[0] == " ":
                    text = text[1:]
                if len(text) > 0:
                    if text[-1] == " ":
                        text = text[:-1]
                return text
            else:
                return ""
        else:
            return ""

    def create_author_name(self, value):
        
        final_author = ""

        author_name = value
        brackets_content = re.findall('\(.*?\)',value)
        for b in brackets_content:
            author_name = author_name.replace(b, '')
            author_name = author_name.strip()

        split_name = author_name.split(',')
        if len(split_name) > 2:
            final_value = '<a href="/'+self.context.language+'/search?SearchableText=%s">%s</a>' %(value, value)
            return final_value

        new_author = []
        if len(split_name) > 1 and len(split_name) > 0:
            new_author.append(split_name[-1])
            new_author.append(split_name[0])
        elif len(split_name) > 0:
            new_author.append(split_name[0])
        else:
            new_author.append(value)

        final_author_name = " ".join(new_author)
        final_author_name = '<a href="/'+self.context.language+'/search?SearchableText=%s">%s</a>' %(final_author_name, final_author_name)

        final_brackets = []
        final_brackets.append(final_author_name)
        final_brackets.extend(brackets_content)

        final_value = " ".join(final_brackets)

        return final_value

    def create_materials(self, value):
        materials = value.split(',')
        _value = ""
        for i, mat in enumerate(materials):
            if i == (len(materials)-1):
                _value += '<a href="/'+self.context.language+'/search?SearchableText=%s">%s</a>' % (mat.replace('"', "'"), mat)
            else:
                _value += '<a href="/'+self.context.language+'/search?SearchableText=%s">%s</a>, ' % (mat.replace('"', "'"), mat)

        return _value

    def create_production_field(self, field):

        authors = []
        
        for author in field:
            production = ""

            maker = author['creator']
            qualifier = author['qualifier']
            role = author['role']
            date_of_birth = author['date_of_birth']
            date_of_death = author['date_of_death']

            if maker not in NOT_ALLOWED:

                production = '<a href="/'+self.context.language+'/search?SearchableText=%s">%s</a>' % (maker.replace("(-", "("), maker)

                dates = ""
                if date_of_birth not in NOT_ALLOWED:
                    dates = "%s" %(date_of_birth)
                    if date_of_death not in NOT_ALLOWED:
                        dates = "%s-%s" %(dates, date_of_death)
                elif date_of_death not in NOT_ALLOWED:
                    dates = "%s" %(date_of_death)

                if dates not in NOT_ALLOWED:
                    if production:
                        production = "%s, (%s)" %(production, dates)

                if role not in NOT_ALLOWED:
                    if production:
                        production = "%s (%s)" %(production, role)
                    else:
                        production = "(%s)" %(role)

                authors.append(production)

        final_production = "<p>".join(authors)

        return final_production

    def create_dimension_field(self, field):
        new_dimension_val = []
        dimension_result = ""

        for val in field:
            dimension = ""
            if val['value'] not in NOT_ALLOWED:
                dimension = "%s" %(val['value'])
            else:
                continue
            if val['unit'] not in NOT_ALLOWED:
                dimension = "%s %s" %(dimension, val['unit'].lower())

            if val['type'] not in NOT_ALLOWED:
                dimension = "%s: %s" %(val['type'].lower(), dimension)
            else:
                continue

            if val['part'] not in NOT_ALLOWED:
                dimension = "%s (%s)" %(dimension, val['part'])

            new_dimension_val.append(dimension)

        dimension_result = '<p>'.join(new_dimension_val)
        
        return dimension_result

    def create_general_repeatable(self, field, name):

        values = []

        if "period" in name:
            separator = "<p>"

            for line in field:
                period = line['period']
                place = ""
                reason = line['reason']
                notes = line['notes']

                if period not in NOT_ALLOWED:
                    values.append(period)

                if place not in NOT_ALLOWED:
                    values.append(place)

                if reason not in NOT_ALLOWED:
                    values.append(reason)

                if notes not in NOT_ALLOWED:
                    values.append(notes)

            final_value = separator.join(values)
            return final_value

        else:
            separator = ", "

        for line in field:
            new_line = []
            if type(line) == dict:
                for key, value in line.iteritems():
                    if value not in NOT_ALLOWED:
                        if name in ['object_material', 'object_technique']:
                            new_value = '<a href="/'+self.context.language+'/search?SearchableText=%s">%s</a>' % (value, value)
                            new_line.append(new_value)
                        else:   
                            new_line.append(value)

                final_line = separator.join(new_line)
                values.append(final_line)
            else:
                if line not in NOT_ALLOWED:
                    if name in ['object_material', 'object_technique']:
                        new_value = '<a href="/'+self.context.language+'/search?SearchableText=%s">%s</a>' % (value, value)
                        new_line.append(new_value)
                    else: 
                        values.append(line)

        final_value = "<p>".join(values)

        return final_value

    def create_prod_dating_field(self, field, obj):
        period = None
        start_date = field['start']
        start_date_precision = field['start_precision']
        end_date = field['end']
        end_date_precision = field['end_precision']

        if end_date == start_date:
            end_date = ""

        result = ""

        if period not in NOT_ALLOWED:
            result = "%s" %(period)

        if start_date not in NOT_ALLOWED:
            if result:
                if start_date_precision not in NOT_ALLOWED:
                    result = "%s, %s %s" %(result, start_date_precision, start_date)
                else:
                    result = "%s, %s" %(result, start_date)
            else:
                if start_date_precision not in NOT_ALLOWED:
                    result = "%s %s" %(start_date_precision, start_date)
                else:
                    result = "%s" %(start_date)
    

        if end_date not in NOT_ALLOWED:
            if result:
                if end_date_precision not in NOT_ALLOWED:
                    if end_date_precision != start_date_precision:
                        result = "%s - %s %s" %(result, end_date_precision, end_date)
                    else:
                        result = "%s - %s" %(result, end_date)
                else:
                    result = "%s - %s" %(result, end_date)
            else:
                if end_date_precision not in NOT_ALLOWED:
                    result = "%s %s" %(end_date_precision, end_date)
                else:
                    result = "%s" %(end_date)

        object_period = getattr(obj, 'object_production_period', "")
        if object_period:
            if object_period[0]['period'] == result:
                return ""

        return result

    def create_production_dating_field(self, period_field, obj):
        period = []
        for field in period_field:
            result = self.create_prod_dating_field(field, obj)
            if result not in NOT_ALLOWED:
                period.append(result)

        final_period = "<p>".join(period)
        return final_period

    def create_inscription_field(self, field):
        inscriptions = []

        for line in field:
            _type = line["type"]
            _content = line["content"]

            if _type not in NOT_ALLOWED and _content not in NOT_ALLOWED:
                new_line = "%s: %s" %(_type, _content)
                inscriptions.append(new_line)
            elif _content not in NOT_ALLOWED:
                new_line = "%s" %(_content)
                inscriptions.append(new_line)

        if inscriptions:
            final_inscriptions = "<p>".join(inscriptions)
            return final_inscriptions
        else:
            return ""

    def create_digital_ref_field(self, field):

        refs = []

        for line in field:
            ref = line['reference']
            title = line['description']

            if title not in NOT_ALLOWED and ref not in NOT_ALLOWED:
                new_ref = '<a href="%s" target="_blank">%s</a>' % (ref, title)
                refs.append(new_ref)
            elif title not in NOT_ALLOWED:
                new_ref = title
                refs.append(new_ref)
            elif ref not in NOT_ALLOWED:
                new_ref = '<a href="%s" target="_blank">%s</a>' % (ref, ref)
                refs.append(new_ref)
            else:
                pass

        if refs:
            final_refs = "<p>".join(refs)
            return final_refs
        else:
            return ""

    def create_period_field(self, field, obj, name):

        title = "Period"

        object_dating = getattr(obj, 'object_dating', "")
        value = ""

        if object_dating:
            for line in object_dating:
                if line['start'] not in NOT_ALLOWED:
                    if line['end'] not in NOT_ALLOWED:
                        if line['start'] == line['end']:
                            value = line['start']
                            break

        if field and value:
            if field[0]['period'] == value:
                title = "Dating"

        result = self.create_general_repeatable(field, name)

        return result, title

    def create_production_place(self, field, obj, name):
        values = []
        separator = "<p>"

        for line in field:
            place = line['place']
            if place not in NOT_ALLOWED:
                values.append(place)

        final_value = separator.join(values)
        return final_value

    def get_all_fields_object(self, object):
        object_schema = []
        schema = getUtility(IDexterityFTI, name='Object').lookupSchema()

        state = getMultiAdapter(
                (self.context, self.request),
                name=u'plone_context_state')

        view_type = state.view_template_id()

        if object.portal_type == 'Object':
            for name, field in getFieldsInOrder(schema):
                if name not in ["text", "object_tags", "book_title", "priref", "administration_name", "object_reproduction_reference", "stable_uri"]:
                    value = getattr(object, name, '')
                    if type(value) == list:
                        if "creator" in name or 'object_author' in name:
                            value = self.create_production_field(value)
                            if value:
                                _title = MessageFactory(field.title)

                                if view_type == "double_view":
                                    _title = MessageFactory("People/event(s) involved")

                                new_attr = {"title": self.context.translate(_title), "value": value, "name": name}
                                object_schema.append(new_attr)
                        elif "dimension" in name:
                            value = self.create_dimension_field(value)
                            if value:
                                _title = MessageFactory(field.title)
                                new_attr = {"title": self.context.translate(_title), "value": value, "name": name}
                                object_schema.append(new_attr)
                        elif "dating" in name:
                            value = self.create_production_dating_field(value, object)
                            if value:
                                _title = MessageFactory(field.title)
                                new_attr = {"title": self.context.translate(_title), "value": value, "name": name}
                                object_schema.append(new_attr)
                        elif "inscription" in name:
                            value = self.create_inscription_field(value)
                            if value:
                                _title = MessageFactory(field.title)
                                new_attr = {"title": self.context.translate(_title), "value": value, "name": name}
                                object_schema.append(new_attr)

                        elif "digital_reference" in name:
                            value = self.create_digital_ref_field(value)
                            if value:
                                _title = MessageFactory(field.title)
                                new_attr = {"title": self.context.translate(_title), "value": value, "name": name}
                                object_schema.append(new_attr)

                        elif "object_production_period" in name:
                            final_value, title = self.create_period_field(value, object, name)
                            if final_value:
                                _title = MessageFactory(title)
                                new_attr = {"title": self.context.translate(_title), "value": final_value, "name": name}
                                object_schema.append(new_attr)

                            final_value = self.create_production_place(value, object, name)
                            if final_value:
                                _title = MessageFactory("Place of production")
                                new_attr = {"title": self.context.translate(_title), "value": final_value, "name": name}
                                object_schema.append(new_attr)

                        else:
                            value = self.create_general_repeatable(value, name)
                            if value:
                                _title = MessageFactory(field.title)
                                new_attr = {"title": self.context.translate(_title), "value": value, "name": name}
                                object_schema.append(new_attr)

                    
                    else:
                        value = self.trim_white_spaces(value)
                        if name in ["object_title", "translated_title"]:
                            if "fossielen" in object.absolute_url():
                                value = ""

                        if value not in NOT_ALLOWED:
                            if name in ['technique', 'artist', 'material', 'object_type', 'object_category', 'publisher', 'author', 'illustrator']:
                                if (name == 'artist') or (name == 'author'):
                                    _value = self.create_author_name(value)
                                    value = _value
                                elif (name == 'material') or (name == 'technique'):
                                    _value = self.create_materials(value)
                                    value = _value
                                else:
                                    _value = '<a href="/'+self.context.language+'/search?SearchableText=%s">%s</a>' % (value, value)
                                    value = _value

                            _title = MessageFactory(field.title)
                            new_attr = {"title": self.context.translate(_title), "value": value, "name": name}
                            
                            if name in ['artist', 'author']:
                                object_schema.insert(0, new_attr)
                            else:
                                object_schema.append(new_attr)
            
            #object_title = getattr(object, 'title', '')
            #new_attr = {'title': self.context.translate('Title'), "value": object_title}

            """if len(object_schema) > 1 and object_schema[0]['name'] == "author":
                if object_schema[1]['name'] == "illustrator":
                    if object.book_title != '':
                        new_attr = {'title': self.context.translate('Title'), "value": object.book_title}
                        object_schema.insert(2, new_attr)
                else:
                    if object.book_title != '':
                        new_attr = {'title': self.context.translate('Title'), "value": object.book_title}
                        object_schema.insert(1, new_attr)

            if len(object_schema) > 1 and object_schema[0]['name'] == "artist":
                object_schema.insert(1, new_attr)
            elif len(object_schema) > 1 and object_schema[0]['name'] != "artist" and object_schema[0]['name'] != "author":
                object_schema.insert(0, new_attr)"""

            obj_body = self.get_object_body(object)
            object_schema.append({"title": "body", "value":obj_body})
        else:
            object_schema = []

        return object_schema

    def getJSON(self):
        schema = []
        if self.context.portal_type == "Object":
            obj = self.context
            schema = self.get_all_fields_object(obj)

        return json.dumps({'schema':schema})


class CollectionSlideshow(BrowserView):
    def getImageObject(self, item):
        if item.portal_type == "Image":
            return item.getObject()

        if item.hasMedia and item.leadMedia != None:
            uuid = item.leadMedia
            media_object = uuidToObject(uuid)
            if media_object:
                return "%s%s" %(media_object.absolute_url(), "/@@images/image/large")

        return ""

    def get_collection_items(self):
        collection_items = []
        if self.context.portal_type == "Collection":
            collection_obj = self.context
            brains = collection_obj.queryCatalog(batch=False)
            results = list(brains)
            
            for item in results[1:]:
                if item.portal_type == "Link" and item.leadMedia:
                    image = self.getImageObject(item)
                    obj_id = obj.getId()
                    obj = item.getObject()
                    data_description = obj.Description()
                    data_title = obj.Title()
                    data_url = obj.absolute_url()

                    collection_items.append({
                        "_id": obj_id,
                        "is_video": True,
                        "remote_url": obj.remoteUrl,
                        "has_overlay": True,
                        "data_description": data_description,
                        "data_title": data_title,
                        "data_url": data_url,
                        "image_path": image
                    });

                elif item.portal_type == "Link" and not item.leadMedia:
                    obj = item.getObject()
                    obj_id = obj.getId()
                    data_description = obj.Description()
                    data_title = obj.Title()
                    data_url = obj.absolute_url()
                    collection_items.append({
                        "_id": obj_id,
                        "is_video": True,
                        "remote_url": obj.remoteUrl,
                        "has_overlay": False,
                        "data_description": data_description,
                        "data_title": data_title,
                        "data_url": data_url,
                        "image_path": ""
                    });

                elif item.portal_type == "Object" or item.portal_type == "Event":
                    obj = item.getObject()
                    obj_id = obj.getId()
                    data_description = obj.Description()
                    data_title = obj.Title()
                    data_url = obj.absolute_url()
                    image = self.getImageObject(item)

                    collection_items.append({
                        "_id": obj_id,
                        "is_video": False,
                        "remote_url": "",
                        "has_overlay": False,
                        "data_description": data_description,
                        "data_title": data_title,
                        "data_url": data_url,
                        "image_path": image
                    });

        return json.dumps(collection_items)


