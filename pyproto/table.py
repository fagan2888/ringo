
import csv
import os
import condition
import string
import value
import aggregator
import pdb
import types
from operator import __and__
from value import Value
from xml.dom.minidom import parse

class Table:

	def __init__(self, filename=None, name=None):
		self.columns = []
		self.types = []
		self.data = []
		self.dumpcnt = 0
		self.name = None
		if not filename is None:
			self.load(filename)
		if not name is None:
			self.name = name

	def setColumnNames(self, columns):
		for col in columns:
			self.columns.append(col)

	def load(self, filename):
		"""
		Load data from either XML or TSV file
		"""
		f = open(filename, 'r')
		_,ext = os.path.splitext(filename);
		if ext=='.xml':
			# Parse the XML file
			dom = parse(f)
			f.close()
			self.name = dom.documentElement.tagName
			xmlrows = dom.getElementsByTagName('row')
			for xmlrow in xmlrows:
				attr = xmlrow.attributes
				for i in range(attr.length):
					name = attr.item(i).name
					if not name in self.columns:
						# Add column to the table
						elt = Value(attr.item(i).value)
						self.columns.append(name)
						self.types.append(elt.getType())
						for r in self.data:
							r.append(Value())
				row = [unicode(xmlrow.getAttribute(name)) for name in self.columns]
				self.addrow(row)
		else:
			# Assume the input is a TSV file
			data = csv.reader(f,delimiter='\t')
			init = True
			for row in data:
				if init:
					self.columns = ['']*len(row)
					self.types = [type(None)]*len(row)
					init = False
				self.addrow([cell.decode('unicode-escape') for cell in row])

	def addrow(self, strrow):
		assert len(strrow) == len(self.columns)
		row = []
		for i in range(len(strrow)):
			val = Value(strrow[i])
			#print str(val.getType())+' et '+str(self.types[i])
			if self.types[i] is type(None):
				# Initialize type
				self.types[i] = val.getType()
				row.append(val)
			elif val.getType() == self.types[i] or val.getType() is type(None):
				row.append(val)
			else:
				row.append(Value(val=strrow[i]))
				if self.types[i] != unicode:
					# Convert all other values in the column back to string
					# TODO : handle more fine-grained fallback (eg Float to Int)
					for r in self.data:
						if not r[i].getType() is type(None):
							r[i] = Value(val=unicode(r[i]))
					self.types[i] = unicode
		self.data.append(row)

	def write(self, filename):
		"""
		Write the data to a TSV file
		"""
		f = open(filename,'wb')
		wr = csv.writer(f,delimiter='\t',quoting=csv.QUOTE_ALL)
		for row in self.data:
			strrow = []
			for cell in row:
				strrow.append(unicode(cell).encode('unicode-escape'))
			wr.writerow(strrow)
		f.close()

	def dump(self,n=-1,reset=False):
		"""
		Dumps n rows of the table to console.
		If reset=True, the dump starts over from the 1st row
		"""
		if n == -1:
			n = self.numRows()
		if reset:
			self.dumpcnt = 0
		colwidth = 17
		join = lambda l: '| '+' | '.join(l)+' |'
		dump = join([string.center(name[:colwidth],colwidth) for name in self.columns])
		sep = '+'*len(dump)
		dump = sep+'\n'+dump+'\n'+sep
		for i in [x+self.dumpcnt for x in range(n)]:
			if i >= len(self.data):
				break
			dump += '\n'+join([string.ljust(str(val)[:colwidth],colwidth) for val in self.data[i]])
			self.dumpcnt += 1
		dump += '\n'+sep
		print dump

	def name(self):
		return self.name

	def getRow(self, i):
		return self.data[i]

	def getColumnById(self, j):
		return [row[j] for row in self.data]

	def getColumnByAttr(self, attribute):
		return self.getColumnById(self.columns.index(attribute))

	def numRows(self):
		return len(self.data)

	def numColumns(self):
		return len(self.columns)

	def newTable(self):
		table = Table(name=self.name)
		table.columns = self.columns[:]
		table.types = self.types[:]
		return table

	def copy(self):
		table = self.newTable()
		table.data = [row[:] for row in self.data]
		return table

	def select(self, col, condition):
		table = self.newTable()
		colIdx = self.colIndex(col)
		f = lambda row: reduce(__and__,[c.eval(row[colIdx]) for c in condition])
		try:
			table.data = [row[:] for row in (filter(f,self.data))]
		except TypeError:
			# only one condition
			table.data = [row[:] for row in (filter(lambda row:condition.eval(row[colIdx]),self.data))]
		return table

	def group(self, attributes, aggregation_attr=None, aggregation_function=None):
		aggregate = not aggregation_attr is None
		# Project table
		tproj = self.project(attributes)
		# Find values for aggregation
		if aggregate:
			agg = aggregator.Aggregator(aggregation_function)
			if not aggregation_attr in self.columns:
				assert aggregation_function == "cnt"	
				aggregationCol = [0]*self.numRows()
			else:
				aggregationCol = self.getColumnByAttr(aggregation_attr)
		# Find groups of rows
		groups = {}
		for i in range(tproj.numRows()):
			row = tproj.data[i]
			key = tuple(row)
			if not key in groups:
				groups[key] = []
			if aggregate:
				groups[key].append(aggregationCol[i])
		# Create final table
		t = tproj.newTable()
		if aggregate:
			t.columns.append(aggregation_attr)
			if not aggregation_attr in self.columns:
				t.types.append(types.FloatType)
			else:
				t.types.append(self.types[t.columns.index(aggregation_attr)])
		# Fill-in rows
		for key in groups:
			newrow = list(key)
			if aggregate:
				newrow.append(agg.calc(groups[key]))
			t.data.append(newrow)
		return t

	def project(self, attributes):
		table = Table(name=self.name)
		indexes = tuple(self.columns.index(att) for att in attributes)
		table.columns = attributes
		table.types = [self.types[i] for i in indexes]
		for row in self.data:
			table.data.append([row[i] for i in indexes])
		return table

	def colIndex(self, attribute):
		if isinstance(attribute,basestring):
			return self.columns.index(attribute)
		else:
			return tuple(self.columns.index(att) for att in attribute)

	def getTypes(self, attributes):
		return list(self.types[i] for i in self.colIndex(attributes))

	def getElmtsAtIdx(self, row, indexes):
		return [row[i] for i in indexes]

	def getElmts(self, row, attributes):
		indexes = self.colIndex(attributes)
		return self.getElmtsAtIdx(row, indexes)

	def join(self, table):
		# Initialize index list to join more efficiently
		colset1 = set(self.columns)
		colset2 = set(table.columns)
		common = list(colset1.intersection(colset2))
		addcol1 = list(colset1.difference(colset2))
		addcol2 = list(colset2.difference(colset1))
		joinIdx1 = self.colIndex(common)
		joinIdx2 = table.colIndex(common)
		addcol1Idx = self.colIndex(addcol1)
		addcol2Idx = table.colIndex(addcol2)
		# Join
		t = Table()
		t.columns = common+addcol1+addcol2
		if self.getTypes(common) != table.getTypes(common):
			print 'Warning: attempting to join on incompatible types'
		t.types = self.getTypes(common+addcol1)+table.getTypes(addcol2)
		for row1 in self.data:
			for row2 in table.data:
				elmts1 = [row1[i] for i in joinIdx1]
				elmts2 = [row2[i] for i in joinIdx2]
				if elmts1 == elmts2:
					row = elmts1+self.getElmtsAtIdx(row1,addcol1Idx)+table.getElmtsAtIdx(row2,addcol2Idx)
					t.data.append(row)
		return t

	def rename(self, oldattr, newattr, copy=True):
		t = self.copy() if copy else self
		oldIdx = self.colIndex(oldattr)
		if isinstance(oldattr,basestring):
			# Rename one attribute
			t.columns[oldIdx] = newattr
		else:
			# Rename list of attributes
			for idx,new in zip(oldIdx,newattr):
				t.columns[idx] = new
		return t

	def getAttrDict(self, row, attributes):
		attrIdx = self.colIndex(attributes)
		attrDict = {}
		for attr,idx in zip(attributes,attrIdx):
			attrDict[attr] = row[idx]
		return attrDict