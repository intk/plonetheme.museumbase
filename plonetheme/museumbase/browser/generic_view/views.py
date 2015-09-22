from ..views import ContentView
from plone.dexterity.browser.view import DefaultView
from plone.app.textfield.value import RichTextValue

class FullView(DefaultView, ContentView):


	def transform_value(self, value):
		if value == "selected":
			value = "Ja"
		return value


	def show_fieldset(self, fieldset):
		for widget in fieldset.widgets.values():
			if widget.value:
				return True
		return False

	def append_value(self, _list, value):
		if value != "" and value != None and value != " ":
			_list.append(value)

	def generate_value_from_item(self, item, line):
		if type(item) is str:
			self.append_value(line, self.transform_value(item))
		else:
			for key in item.keys():
				self.append_value(line, self.transform_value(item[key]))

	def get_field_value(self, value, widget): 
		_type = type(value)
		if _type is list:
			try:
				result = []
				for item in value:
					line = []
					self.generate_value_from_item(item, line)
					line = ', '.join(line)
					
					result.append(line)
				result = '<p>'.join(result)
				return result
			except:
				pass
				return value
		return value
