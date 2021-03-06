"""
	# Author: Robert Cudmore
	# Date: 20191115

	This is a napari plugin to manager a list of shapes and perform analysis.

	For each image in a stack or time-series,
		For 'line' shape, calculates the width from the intensity profile.
		For 'rectangle' shape, calculates mean/min/max/sd/n

	Saves/loads shape analysis dictionaries and image files (kymographs) in h5f file.

	Requires:
	 - ShapeAnalysis.py

	Important:
	 - We are managing self.shapeLayer.metadata, append on new, pop on delete
	 
	Todo:
	 - rewrite code to use native napari plotting with VisPy, we are currently using PyQtGraph
	 - Work with napari developers to create API to manage shapes (add, delete, move, drag vertex, etc. etc.)
	 - Detatch from pImpy and make a simple 2 file standalone github repo (bShapeAnalysisWidget.py, bShapeAnalysis.py)

	See:
	 - [WIP] Histogram with 2-way LUT control #675
	   https://github.com/napari/napari/pull/675
	 - Receive events on shape create and delete #720
	   https://github.com/napari/napari/issues/720
	 - Shape layer analysis plugin ... #719
	   https://github.com/napari/napari/issues/719
"""

import os, time, json
import numpy as np
import h5py

#from scipy.ndimage import gaussian_filter
import scipy.ndimage

import pyqtgraph as pg

import napari

from PyQt5 import QtGui, QtSql, QtCore, QtWidgets

import vispy.app
import vispy.plot as vp

#import bimpy #
from ShapeAnalysis import ShapeAnalysis # backend analysis
from myPyQtGraphWidget import myPyQtGraphWidget


"""
class myVisPyWindow(QtWidgets.QWidget):
	def __init__(self):
		super(myVisPyWindow, self).__init__()

		self.sliceLinesList = []

	def buildVisPyInterface(self):

		# vispy
		#canvas = vispy.app.Canvas()
		fig = vp.Fig(size=(800, 600))

		data = np.random.rand(100, 2)
		self.linePlotWidget = fig[0, 0] # this creates a PlotWidget
		self.linePlot = self.linePlotWidget.plot(data, title='Line Intensity', xlabel='Points', ylabel='Intensity')
		#self.linePlot = fig[0, 0].plot(data, title='Line Intensity', xlabel='Points', ylabel='Intensity')

		self.myHBoxLayout = QtWidgets.QHBoxLayout(self)

		self.myHBoxLayout.addWidget(QtWidgets.QPushButton('A Button'))
		self.myHBoxLayout.addWidget(fig.native)

		self.show()

		print('buildVisPyInterface() done')
"""


class ShapeAnalysisPlugin:
	"""
	handle interface of one shape roi at a time

	uses ShapeAnalysis for back end analysis
	"""
	#def __init__(self, napariViewer, path=None, myStack=None):
	#def __init__(self, napariViewer, imageLayer=None, imagePath=None):
	def __init__(self, imagePath=None):
		"""
		napariViewer: existing napari viewer
		imageLayer: napari image layer to use as image
			e.g. imageLayer.data

		Assuming:
			imageLayer.data is (slices, rows, col)
		"""

		# start pulled from main
		title = ''
		if imagePath is not None:
			title = os.path.basename(imagePath)

		self.napariViewer = napari.Viewer(title=title)

		# add image as layer
		colormap = 'green'
		scale = (1,1,1) #(1,0.2,0.2)
		self.myImageLayer = self.napariViewer.add_image(
			#self.myStack.stack[0,:,:,:],
			path = path,
			colormap=colormap,
			scale=scale)
		# end pulled from main

		self.sliceNum = 0

		#self.napariViewer = napariViewer
		#self.myImageLayer = imageLayer
		self.path = imagePath

		self.filterImage() # filter the raw image for analysis

		self.analysis = ShapeAnalysis(self.imageData) # self.imageData is a property

		# make an empty shape layer
		self.shapeLayer = self.napariViewer.add_shapes(
			name=self.myImageLayer.name + '_shapes',
		)
		self.shapeLayer.mode = 'select' #'select'
		self.shapeLayer.metadata = []

		self.myPyQtGraphWidget =  myPyQtGraphWidget(self.shapeLayer)

		"""
		# not sure what these were doing ?
		self.shapeLayer.events.mode.connect(self.layerChangeEvent)
		self.shapeLayer.events.opacity.connect(self.layerChangeEvent)
		self.shapeLayer.events.edge_width.connect(self.layerChangeEvent)
		self.shapeLayer.events.face_color.connect(self.layerChangeEvent)
		self.shapeLayer.events.edge_color.connect(self.layerChangeEvent)
		# this event does not exist, todo: work with napari developers to implement
		#self.shapeLayer.events.removed.connect(self.layerChangeEvent)
		"""

		# callback for user changing slices
		self.napariViewer.dims.events.axis.connect(self.my_update_slider)

		self.mouseBindings() # map key strokes to funciton calls
		self.keyboardBindings() # map mouse down/drag to function calls

		#todo: depreciate this
		# build second window to show results of shape analysis
		self.buildPyQtGraphInterface()

		#self.buildVisPyInterface()
		#self.myVisPyWindow = myVisPyWindow()

		self.load()

	def buildPyQtGraphInterface(self):
		"""
		Depreciated, use myPyQtGraphWidget instead
		"""
		#
		# pyqt graph plots
		self.pgWin = pg.GraphicsWindow(title="Shape Analysis Plugin") # creates a window
		#self.pgWin = pg.QGraphicsLayoutWidget(title="Shape Analysis Plugin") # creates a window

		pgRow = 0 # row of pyqtgraph

		# keep a list of vertical lines to indicate slice in each plot
		self.sliceLinesList = []

		#
		# (1) line intensity profile for one slice
		self.lineIntensityPlotItem = self.pgWin.addPlot(title="Line Intensity Profile", row=pgRow, col=0)
		self.lineIntensityPlotItem.setLabel('left', 'Intensity', units='')
		self.lineIntensityPlotItem.setLabel('bottom', 'Line Profile', units='')
		self.lineProfilePlot = self.lineIntensityPlotItem.plot(name='lineIntensityProfile')
		self.lineProfilePlot.setShadowPen(pg.mkPen((255,255,255), width=2, cosmetic=True))
		# fit
		x = y = []
		# gaussian
		self.fitPlot = self.lineIntensityPlotItem.plot(x, y, pen=pg.mkPen('r', width=3), name='fit')
		# heuristic
		self.fitPlot2 = self.lineIntensityPlotItem.plot(x, y, pen=pg.mkPen('b', symbol='.', symbolSize=10, width=5), name='fitPoints')

		pgRow += 1

		#
		# (2) diameter for each slice
		self.analysisPlotItem = self.pgWin.addPlot(title='', row=pgRow, col=0)
		self.analysisPlotItem.setLabel('left', 'Diameter', units='')
		#self.analysisPlotItem.setLabel('bottom', 'Slices') #, units='s')
		# vertical line showing slice number selection in napari viewer
		#self.sliceLineDiameter = pg.InfiniteLine(pos=0, angle=90)
		sliceLine = pg.InfiniteLine(pos=0, angle=90)
		self.sliceLinesList.append(sliceLine)
		self.analysisPlotItem.addItem(sliceLine)
		#
		self.analysisDiameter = self.analysisPlotItem.plot(name='lineintensitydiameter')

		pgRow += 1

		#
		# (3) image with slices on x, and intensity of each line profile on y
		self.stackLineIntensityImage = self.pgWin.addViewBox(row=pgRow, col=0)
		# setLabel does not work for view box?
		#self.stackLineIntensityImage.setLabel('left', 'Line Intensity Profile') #, units='A')
		#self.stackLineIntensityImage.setLabel('bottom', 'Slices') #, units='s')

		self.img = pg.ImageItem()
		self.stackLineIntensityImage.addItem(self.img)

		# add a vertical line for current slice (over image)
		#self.sliceLineProfileImage = pg.InfiniteLine(pos=0, angle=90)
		#self.stackLineIntensityImage.addItem(self.sliceLineProfileImage)
		sliceLine = pg.InfiniteLine(pos=0, angle=90)
		self.sliceLinesList.append(sliceLine)
		self.stackLineIntensityImage.addItem(sliceLine)

		pgRow += 1

		# (4) intensity of polygon for each slice
		self.polygonPlotItem = self.pgWin.addPlot(title='', row=pgRow, col=0)
		self.polygonPlotItem.setLabel('left', 'Mean Polygon Intensity') #, units='A)
		self.polygonPlotItem.setLabel('bottom', 'Slices') #, units='s')
		# vertical line showing slice number selection in napari viewer
		#self.verticalSliceLine3 = pg.InfiniteLine(pos=0, angle=90)
		#self.polygonPlotItem.addItem(self.verticalSliceLine3)
		sliceLine = pg.InfiniteLine(pos=0, angle=90)
		self.sliceLinesList.append(sliceLine)
		self.polygonPlotItem.addItem(sliceLine)
		#
		self.analysisPolygonMean = self.polygonPlotItem.plot(symbolSize=3, name='analysisPolygonMean')
		#self.analysisPolygonMin = self.polygonPlotItem.plot(name='analysisPolygonMin')
		#self.analysisPolygonMax = self.polygonPlotItem.plot(name='analysisPolygonMax')

		# all polygon mean across all shapes/rois
		self.polygonMeanListPlot = []
		#self.polygonMeanListPlot.append(self.polygonPlotItem.plot(name='polygonMeanListPlot'))

		# (5) tree view of all shapes
		'''
		w = pg.TreeWidget()
		w.setColumnCount(2)
		w.show()
		w.resize(500,500)
		w.setWindowTitle('pyqtgraph example: TreeWidget')

		i1  = QtGui.QTreeWidgetItem(["Item 1"])
		i2  = QtGui.QTreeWidgetItem(["Item 2"])
		i3  = QtGui.QTreeWidgetItem(["Item 3"])
		w.addTopLevelItem(i1)
		w.addTopLevelItem(i2)
		w.addTopLevelItem(i3)

		# does not work
		#self.pgWin.addItems(w)
		'''

	def mouseBindings(self):
		@self.shapeLayer.mouse_drag_callbacks.append
		def shape_mouse_move_callback(layer, event):
			"""respond to mouse_down """
			self.myMouseDown_Shape(layer, event)

		# this decorator cannot point to member function directly because it needs 'yield'
		# put inline function with 'yield' right after decorator
		# and then call member functions from within
		@self.shapeLayer.mouse_drag_callbacks.append
		def shape_mouse_drag_callback(layer, event):
			### respond to click+drag """
			#print('shape_mouse_drag_callback() event.type:', event.type, 'event.pos:', event.pos, '')
			self.lineShapeChange_callback(layer, event)
			yield

			while event.type == 'mouse_move':
				self.lineShapeChange_callback(layer, event)
				yield

	def keyboardBindings(self):
		"""
		set up keyboard callbacks

		todo: here, we bind to the shape layer, we may want to bind to the viewer with:
		@viewer.bind_key('m')
		"""

		@self.shapeLayer.bind_key('h', overwrite=True)
		def shape_user_keyboard_h(layer):
			""" print help """
			print('=== bShapeAnalysisWidget Help')
			print('l: Create new line shape')
			print('r: Create new rectangle shape')
			print('Delete: Delete selected shape')
			print('u: Update analysis on selected shape')
			print('Command+Shift+L: Load h5f file (prompt user for file)')
			print('Command+l: Load default h5f file (each .tif has corresponding h5f file)')
			print('Command+s: Save default h5f file (each .tif has corresponding h5f file)')

		@self.shapeLayer.bind_key('l', overwrite=True)
		def shape_user_keyboard_l(layer):
			""" create/add new line shape, user should not use napari icon to create shape """
			print('=== shape_user_keyboard_l() layer:', layer)
			self.addNewDefaultLine()

		@self.shapeLayer.bind_key('r', overwrite=True)
		def shape_user_keyboard_r(layer):
			""" create/add new rectangle shape, user should not use napari icon to create shape """
			print('=== shape_user_keyboard_r() layer:', layer)
			self.addNewDefaultRectangle()

		@self.shapeLayer.bind_key('Backspace', overwrite=True)
		def shape_user_keyboard_Backspace(layer):
			""" delete selected shape """
			print('=== shape_user_keyboard_Backspace() layer:', layer)
			self._deleteShape()

		@self.napariViewer.bind_key('u')
		def user_keyboard_u(viewer):
			""" update analysis """
			print('=== user_keyboard_u')
			self.updateAnalysis()

		'''
		@self.napariViewer.bind_key('n')
		def user_keyboar_n(viewer):
			""" spawn a new shape analysis plugin? """
			print('=== user_keyboard_n')
			# viewer.active_layer
			#print('viewer.layers:', viewer.layers)
			for layer in self.napariViewer.layers:
				print('type(layer).__name__:', type(layer).__name__)
				print('   layer.name:', layer.name)
				print('   layer.selected:', layer.selected)
		'''

		@self.napariViewer.bind_key('Control-Shift-l')
		def loadOtherFile(viewer):
			print('=== loadOtherFile')
			#self.load()

		@self.napariViewer.bind_key('Control-l', overwrite=True)
		def user_keyboar_l(viewer):
			print('=== user_keyboard_l')
			self.load()

		@self.napariViewer.bind_key('Control-s', overwrite=True)
		def user_keyboar_s(viewer):
			print('=== user_keyboard_s')
			self.save()

	def filterImage(self):
		""" not working, just playing around """
		print('filterImage() calculating the difference for 3d image:', self.myImageLayer.data.shape)
		startTime = time.time()
		self.filtered = scipy.ndimage.gaussian_filter(self.myImageLayer.data, sigma=1)
		#self.filtered = scipy.ndimage.median_filter(self.myImageLayer.data, size=3)

		"""
		print('   self.myImageLayer.data.dtype:', self.myImageLayer.data.dtype)
		print('   self.filtered.dtype:', self.filtered.dtype)
		self.difference = None
		"""

		"""
		self.difference = np.ndarray(shape=self.filtered.shape, dtype=np.int16) #np.ndarray(self.filtered.shape)
		for idx, slice in enumerate(range(self.difference.shape[0])):
			if idx>3:
				self.difference[idx,:,:] = self.filtered[idx,:,:] - self.filtered[idx-4,:,:]
			print('   self.difference.dtype:', self.difference.dtype)
		"""

		stopTime = time.time()
		print('   took', round(stopTime-startTime,2), 'seconds')

		"""
		# append image to napari
		self.differenceImage = self.napariViewer.add_image(
			data = self.difference if self.difference is not None else self.filtered,
			name=self.myImageLayer.name + '_diff',
		)
		print('   done')
		"""

	def _deleteShape(self):
		""" Delete selected shape, from napari and from pyqtgraph"""

		shapeType, index, data = self._getSelectedShape()

		print('_deleteShape()')
		print('   shapeType:', shapeType)
		print('   index:', index) # absolute shape index
		print('   data:', data)

		# (1)
		if shapeType == 'rectangle':
			# we can't use index as it includes all shapes, we need index into rectangle to remove?
			rectangleIndex = self._getRectangleIndex(index)
			# before we delete, clear the plot
			self.polygonMeanListPlot[rectangleIndex].setData([], [], connect='finite')
			# remove the plot
			self.polygonMeanListPlot.pop(rectangleIndex) # remove from self.polygonMeanListPlot

			self.myPyQtGraphWidget.shape_delete(index)
		
		# delete from napari
		# order matters, this has to be after (1) above
		self.shapeLayer.remove_selected() # remove from napari
		# we are managing metadata list (append on new shape, pop on delete)
		self.shapeLayer.metadata.pop(index)

		# todo: this is not updating correctly, it is not removing the newly deleted rectangle analysis
		self.updatePlots() #refresh plots

		self.myPyQtGraphWidget.plotAllPolygon(None)
		
	def _getRectangleIndex(self, shapeIndex):
		"""
		Given the absolute index of a shape, return the index based on number of rectangles

		Parameters:
			shapeIndex: absolute shape index
		"""
		theRectangleIndex = None
		rectangleIdx = 0
		for idx, shapeType in enumerate(self.shapeLayer.shape_types):
			print('looking for rectangle at shapeIndex:', shapeIndex, 'idx:', idx, 'shapeType:', shapeType)
			if shapeType == 'rectangle':
				if idx == shapeIndex:
					theRectangleIndex = rectangleIdx
					break
				rectangleIdx += 1
		print('_getRectangleIndex() returning theRectangleIndex:', theRectangleIndex)
		return theRectangleIndex

	def _addNewShape(self, shapeDict):
		""" Add a new shape """

		self.shapeLayer.add(
			data = shapeDict['data'],
			shape_type = shapeDict['shape_type'],
			edge_width = shapeDict['edge_width'],
			edge_color = 'coral',
			face_color = 'royalblue',
			opacity = shapeDict['opacity'])

		metaDataDict = {
			'lineDiameter': np.zeros((0)),
			'lineKymograph': np.zeros((1,1)),
			'polygonMin': np.zeros((0)),
			'polygonMax': np.zeros((0)),
			'polygonMean': np.zeros((0)),
		}

		self.shapeLayer.metadata.append(metaDataDict)

	def addNewDefaultLine(self):
		"""
		Add a new line shape, in response to user keyboard 'l'
		"""
		src = [20,20]
		dst = [100,100]
		shapeDict = {
			'shape_type': 'line',
			'edge_width': 5,
			'opacity': 0.5,
			'data': np.array([src, dst])
		}
		self._addNewShape(shapeDict)

		# analyze one line
		sliceNum = self.sliceNum
		x, oneProfile, fit, fwhm, leftIdx, rightIdx = self.analysis.lineProfile(sliceNum, src, dst, linewidth=1, doFit=True)

		# update plot
		self.myPyQtGraphWidget.updateLinePlot(x, oneProfile, fit=fit, leftIdx=leftIdx, rightIdx=rightIdx)

	def addNewDefaultRectangle(self):
		"""
		Add a new rectangle shape, in response to user keyboard 'r'
		"""
		shapeDict = {
			'shape_type': 'rectangle',
			'edge_width': 3,
			'opacity': 0.2,
			'data': np.array([[50, 50], [50, 80], [80, 80], [80, 50]])
		}
		self._addNewShape(shapeDict)

	def _getSavePath(self):
		path, filename = os.path.split(self.path)
		savePath = os.path.join(path, os.path.splitext(filename)[0] + '.h5')
		return savePath

	def save(self):
		"""
		Save all shapes and analysis to a h5f file

		todo: save each of (shape_types, edge_colors, etc) as a group attrs rather than a dict
		todo: migrate this to ShapeAnalysis class to be used from Jupyter notebook (without napari interface)
		"""
		print('=== bShapeAnalysisWidget.save()')
		#print(type(self.shapeLayer.data[0]))

		# create a dict for each shape/roi
		shapeList = []
		for idx, shapeType in enumerate(self.shapeLayer.shape_types):
			#print('   idx:', idx, shapeType)
			shapeDict = {
				#'data:', self.shapeLayer.data[idx],
				'shape_types': self.shapeLayer.shape_types[idx],
				'edge_colors': self.shapeLayer.edge_colors[idx],
				'face_colors': self.shapeLayer.face_colors[idx],
				'edge_widths': self.shapeLayer.edge_widths[idx],
				'opacities': self.shapeLayer.opacities[idx],
				#z_indices for polygon is int64 and can not be with json.dumps ???
				#'z_indices': int(self.shapeLayer.z_indices[idx]),
			}
			#print('   shapeDict:', shapeDict)
			shapeList.append(shapeDict)

			# check the types
			# z_indices is int64 and is not serializable ???
			'''
			for k, v in shapeDict.items():
				print('***', k, v, type(v))
			'''

		# write each shape dict to an h5f file
		h5File = self._getSavePath()
		print('writing', len(shapeList), 'shapes to file:', h5File)
		#h5File = self.myImageLayer.name + '_shapeAnalysis.h5'
		with h5py.File(h5File, "w") as f:
			for idx, shape in enumerate(shapeList):
				print('   idx:', idx, 'shape:', shape)
				# each shape will have a group
				shapeGroup = f.create_group('shape' + str(idx))
				# each shape group will have a shape dict with all parameters to draw ()
				shapeDict_json = json.dumps(shape)
				shapeGroup.attrs['shapeDict'] = shapeDict_json
				# each shape group will have 'data' with coordinates of polygon
				shapeData = self.shapeLayer.data[idx]
				shapeGroup.create_dataset("data", data=shapeData)

				#print('self.shapeLayer.metadata[idx]:', self.shapeLayer.metadata[idx])
				for k,v in self.shapeLayer.metadata[idx].items():
					newGroup = 'metadata/' + k
					print('      ', newGroup)
					shapeGroup.create_dataset(newGroup, data=v)

	def load(self):
		"""
		Load shapes and analysis from h5f file

		todo: migrate this to ShapeAnalysis class to be used from Jupyter notebook (without napari interface)
		"""
		h5File = self._getSavePath()
		print('=== bShapeAnalysisWidget.load() file:', h5File)
		shape_type = []
		edge_width = []
		edge_color = []
		face_color = []
		with h5py.File(h5File, "r") as f:
			# iterate through h5py groups (shapes)
			shapeList = []
			linesList = []
			#metadataList = [] # metadata is a special case
			for name in f:
				print('loading name:', name)
				json_str = f[name].attrs['shapeDict']
				json_dict = json.loads(json_str) # convert from string to dict
				'''
				print('   json_dict:', json_dict)
				print('   type(json_dict):', type(json_dict))
				print('   json_dict["edge_colors"]', json_dict['edge_colors'])
				'''
				# load the coordinates of polygon
				data = f[name + '/data'][()] # the wierd [()] converts it to numpy ndarray

				#metadata = f[name + '/metadata'][()] # the wierd [()] converts it to numpy ndarray
				metadataDict = {}
				for name2 in f[name + '/metadata']:
					#print('name2:', name2)
					metadataDict[name2] = f[name + '/metadata' + '/' + name2][()]
				'''
				print('   data:', data)
				print('   type(data)', type(data))
				'''

				linesList.append(data)
				#metadataList.append(metadataDict) # metadata is a special case
				self.shapeLayer.metadata.append(metadataDict)

				shapeDict = json_dict
				shapeDict['data'] = data

				shape_type.append(shapeDict['shape_types'])
				edge_width.append(shapeDict['edge_widths'])
				edge_color.append(shapeDict['edge_colors'])
				face_color.append(shapeDict['face_colors'])

				#print("type(shapeDict['edge_colors'])", type(shapeDict['edge_colors']))

				shapeList.append(shapeDict)

		'''
		print('linesList:', linesList)
		print('edge_color:', edge_color)
		print('type(edge_color[0]):', type(edge_color[0]))

		print('self.shapeLayer.metadata:', self.shapeLayer.metadata)
		'''

		# create a shape from what we loaded
		print('=== Appending', len(linesList), 'loaded shapes to shapes layer')

		# metadata is a special case
		#self.shapeLayer.metadata = metadataList

		#add shapes to existing shape layer
		'''
		# 1)
		# this does not work because vispy is interpreting (edge_color, face_color) as a list
		# and thus expecting rgb (or rgba?) and not string like 'black'
		self.shapeLayer.add(
			linesList,
			shape_type = shape_type,
			edge_width = edge_width,
			edge_color = edge_color,
			face_color = face_color
			)
		'''
		# 2)
		self.shapeLayer.add(
			linesList,
			shape_type = shape_type,
			edge_width = edge_width,
			)

		#self.updatePlots()

		# plot all polygon analysis
		self.myPyQtGraphWidget.plotAllPolygon(None)

	"""
	def buildVisPyInterface(self):

		# vispy
		#canvas = vispy.app.Canvas()
		fig = vp.Fig(size=(800, 600))

		data = np.random.rand(100, 2)
		'''
		self.linePlotWidget = fig[0, 0] # this creates a PlotWidget
		self.linePlot = self.linePlotWidget.plot(data, title='Line Intensity', xlabel='Points', ylabel='Intensity')
		'''
		self.linePlot = fig[0, 0].plot(data, title='Line Intensity', xlabel='Points', ylabel='Intensity')

		# qt
		w = QtWidgets.QMainWindow()
		widget = QtWidgets.QWidget()
		w.setCentralWidget(widget)
		widget.setLayout(QtWidgets.QHBoxLayout())

		widget.layout().addWidget(QtWidgets.QPushButton('A Button'))
		widget.layout().addWidget(fig.native)
		#widget.layout().addWidget(canvas.native)

		w.show()
		#widget.show()
		#vispy.app.run() # this does not return?

		print('buildVisPyInterface() done')
	"""

	'''
	def layerChangeEvent(self, event):
		""" todo: not sure what the purpose of this was? """
		print(time.time(), 'layerChangeEvent() event.type:', event.type)
		respondToTheseEvents = ['edge_width']
	'''

	@property
	def imageData(self):
		"""
		return image data for analysis

		should be using a filtered image
		"""
		#return self.myImageLayer.data
		return self.filtered

	def myMouseDown_Shape(self, layer, event):
		"""
		Detect mouse move in shape layer (not called when mouse is down).

		responds to event.type in (mouse_press)

		event is type vispy.app.canvas.MouseEvent
		see: http://api.vispy.org/en/v0.1.0-0/event.html
		"""
		print('myMouseDown_Shape()', layer, event.type)

		type, index, dict = self._getSelectedShape()
		print('   type:', type)
		print('   index:', index)
		print('   dict:', dict) # (type, index, dict)

		self.updatePlots()

	def lineShapeChange_callback(self, layer, event):
		"""
		Callback for when user clicks+drags to resize a line shape.

		Responding to @self.shapeLayer.mouse_drag_callbacks

		update pg plots with line intensity profile

		get one selected line from list(self.shapeLayer.selected_data)
		"""
		# loop through all lines?
		#for data in self.shapeLayer.data:
		shapeType, index, data = self._getSelectedShape()
		if shapeType == 'line':
			#src = data[0]
			#dst = data[1]
			#self.updateLines(self.sliceNum, src, dst)
			self.updateLines(self.sliceNum, data)
		# turned this off, was too slow
		# todo, just update and then plot polygon analysis for current slice
		'''
		if shapeType in ['rectangle', 'polygon']:
			self.updatePolygon(self.sliceNum, data)
		'''

	def _getSelectedShape(self):
		"""
		Return the selected shape with a tuple (shapeType, index, data)
			shapeType: ('line', 'polygon')
			index:
			data: the data from a shape layer, generally the coordinates of a shape
				- for a line it is a list of two points
				- for a polygon it is a list of N vertex points
		"""
		# selected_data is a list of int with the index into self.shapeLayer.data of all selected shapes
		selectedDataList = self.shapeLayer.selected_data
		#print('selectedDataList:', selectedDataList)
		if len(selectedDataList) > 0:
			index = selectedDataList[0] # just the first selected shape
			shapeType = self.shapeLayer.shape_types[index]
			return shapeType, index, self.shapeLayer.data[index]
		else:
			return (None, None, None)

	def my_update_slider(self, event):
		"""
		Respond to user changing slice/image slider
		"""
		#print('my_update_slider() event:', event)
		if (event.axis == 0):
			# todo: not sure if this if foolproof
			self.sliceNum = self.napariViewer.dims.indices[0]

			self.updateVerticalSliceLines(self.sliceNum)

			self.myPyQtGraphWidget.updateVerticalSliceLines(self.sliceNum)

			# todo: this does not feal right ... fix this !!!
			shapeType, index, data = self._getSelectedShape()
			if shapeType == 'line':
				#src = data[0]
				#dst = data[1]
				#self.updateLines(self.sliceNum, src, dst)
				self.updateLines(self.sliceNum, data)
			'''
			elif shapeType in ['rectangle', 'polygon']:
				self.updatePolygon(self.sliceNum, data)
			'''

	'''
	def updateAnalysis(self):
		shapeType, index, data = self._getSelectedShape()
		if shapeType == 'rectangle':
			theMin, theMax, theMean = self.analysis.stackPolygonAnalysis(data)
			if theMin is None:
				return
	'''
	
	def updateStackPolygon(self, index=None):
		"""
		data is a list of points specifying vertices of a polygon
		a rectangle is just a polygon with 4 evenly spaces vertices
		"""
		print('bShapeAnalysisWidget.updateStackPolygon() index:', index)

		shapeType, index, data = self._getSelectedShape()

		theMin, theMax, theMean = self.analysis.stackPolygonAnalysis(data)

		if theMin is None:
			return

		# store in shape metadata
		#print('self.shapeLayer.metadata:', self.shapeLayer.metadata)
		self.shapeLayer.metadata[index]['polygonMean'] = theMean

		# plot
		self.updatePlots()
		'''
		if shapeType == 'line':
			self.updateStackLinePlot(index)
		elif shapeType == 'rectangle':
			self.updateStackPolygonPlot(index=index)
		'''

		'''
		xPlot = np.asarray([slice for slice in range(len(theMean))])
		self.analysisPolygonMean.setData(xPlot, theMean, connect='finite') # connect 'finite' will make nan(s) disjoint
		'''

	def updatePlots(self):
		"""
		update plots based on current selection

		todo: The logic here is all screwed up. We need to update even if there is not a selection !!!!

		This needs to update (1) a line based on selection and (2) all rectangle shapes/roi, regardless of selection
		"""

		print('updatePlots()')

		shapeType, index, data = self._getSelectedShape()

		# on delete, these will all be None
		print('   shapeType:', shapeType)
		print('   index:', index)
		print('   data:', data)

		# in the end just use this
		self.myPyQtGraphWidget.updateShapeSelection(index)
		
		# update the selected shape
		if shapeType == 'line':
			print('   updating line at index:', index)
			# diameter
			lineDiameter = self.shapeLayer.metadata[index]['lineDiameter']
			xPlot = np.asarray([slice for slice in range(len(lineDiameter))])
			self.analysisDiameter.setData(xPlot, lineDiameter, connect='finite')
			# kymograph
			lineKymograph = self.shapeLayer.metadata[index]['lineKymograph']
			self.img.setImage(lineKymograph)

			# new
			'''
			self.myPyQtGraphWidget.updateDiameterPlot(xPlot, lineDiameter)
			self.myPyQtGraphWidget.updateKymograph(lineKymograph)
			'''
			
		elif shapeType == 'rectangle':
			#
			# plot all rectangle polygonMean
			#
			print('   updating rectangle at index:', index)
			polygonMean = self.shapeLayer.metadata[index]['polygonMean']

			# normalize to first few points
			tmpMean = np.nanmean(polygonMean[0:10])
			polygonMean = polygonMean / tmpMean * 100
			polygonMean += index * 20

			xPlot = np.asarray([slice for slice in range(len(polygonMean))])
			self.analysisPolygonMean.setData(xPlot, polygonMean, connect='finite') # connect 'finite' will make nan(s) disjoint

			# new, selected ractanle
			'''
			self.myPyQtGraphWidget.updateSelectedPolygon(xPlot, polygonMean)
			'''
			
		# first clear all
		for idx in range(len(self.polygonMeanListPlot)):
			self.polygonMeanListPlot[idx].setData([], [], connect='finite')
		# then replot
		numRectangle = 0 # keep track of rectangle number 0, 1, 2, ... to index into self.polygonMeanListPlot
		for idx, type in enumerate(self.shapeLayer.shape_types):
			if type == 'rectangle':
				#numRectangle += 1
				if len(self.polygonMeanListPlot)-1 < numRectangle:
					self.polygonMeanListPlot.append(self.polygonPlotItem.plot(pen=(255,0,0), name='polygonMeanListPlot'+str(idx)))
				if idx == index:
					# skip the one that is selected, plotted above in white
					continue
				print('   appending rectangle for shape idx:', idx)
				polygonMean = self.shapeLayer.metadata[idx]['polygonMean']
				xPlot = np.asarray([slice for slice in range(len(polygonMean))])
				#print(idx, 'polygonMean.shape:', polygonMean.shape)
				if len(polygonMean)<1:
					continue # there is no analysis
				# normalize to first few points
				tmpMean = np.nanmean(polygonMean[0:10])
				polygonMean = polygonMean / tmpMean * 100
				polygonMean += idx * 20

				#print('   DEBUG: idx:', idx, 'len(self.polygonMeanListPlot):', len(self.polygonMeanListPlot))
				self.polygonMeanListPlot[numRectangle].setData(xPlot, polygonMean, connect='finite')

				numRectangle += 1

	def updateAnalysis(self):
		shapeType, index, data = self._getSelectedShape()
		if index is None:
			return
		if shapeType == 'line':
			self.updateStackLineProfile()
		elif shapeType in ['rectangle', 'polygon']:
			self.updateStackPolygon()
		else:
			print('updateAnalysis() unknown shape type:', shapeType)
			return
		# update plots
		self.myPyQtGraphWidget.updateShapeSelection(index)
		
	def updateStackLineProfile(self):
		"""
		generate a line profile for each image in a stack/timeseries

		data: two points that make the line
		"""
		shapeType, index, data = self._getSelectedShape()

		src = data[0]
		dst = data[1]
		print('updateStackLineProfile() src:', src, 'dst:', dst)
		#x, self.lineProfileImage, self.FWHM = self.myStack.analysis.stackLineProfile(src, dst)
		x, lineKymograph, lineDiameter = self.analysis.stackLineProfile(src, dst)

		self.shapeLayer.metadata[index]['lineDiameter'] = lineDiameter
		self.shapeLayer.metadata[index]['lineKymograph'] = lineKymograph

		self.updatePlots()

		'''
		#
		# update plots with new results
		self.img.setImage(self.lineProfileImage)

		xPlot = np.asarray([slice for slice in range(len(self.FWHM))])
		self.analysisDiameter.setData(xPlot, self.FWHM, connect='finite')
		'''

	def updateVerticalSliceLines(self, sliceNum):
		"""
		Set vertical line indicating current slice
		"""
		for line in self.sliceLinesList:
			line.setValue(sliceNum)

	'''
	def updatePolygon(self, sliceNum, data):
		"""
		data is a list of vertex points
		"""
		print('bShapeAnalysisWidget.updatePolygon() data:', data)
		#theMin, theMax, theMean = self.myStack.analysis.polygonAnalysis(sliceNum, data)
		theMin, theMax, theMean = self.analysis.polygonAnalysis(sliceNum, data)
		print('   slice:', sliceNum, 'theMin:', theMin, 'theMax:', theMax, 'theMean:', theMean)
	'''

	def updateLines(self, sliceNum, data):
		"""
		data: two points that make the line
		"""
		src = data[0]
		dst = data[1]
		print('bShapeAnalysisWidget.updateLines() sliceNum:', sliceNum, 'src:', src, 'dst:', dst)
		#x, lineProfile, yFit, fwhm, leftIdx, rightIdx = self.myStack.analysis.lineProfile(sliceNum, src, dst, linewidth=1, doFit=True)
		# this can fail
		x, lineProfile, yFit, fwhm, leftIdx, rightIdx = self.analysis.lineProfile(sliceNum, src, dst, linewidth=1, doFit=True)

		#x = [a for a in range(len(lineProfile))]
		#yFit, fwhm, leftIdx, rightIdx = self.myStack.analysis.fitGaussian(x, lineProfile)

		self.updateLineIntensityPlot(x, lineProfile, yFit, leftIdx, rightIdx)
		#self.updateLineIntensityPlot2(x, lineProfile, yFit, leftIdx, rightIdx)

	def updateLineIntensityPlot2(self, x, oneProfile, fit=None, left_idx=np.nan, right_idx=np.nan): #, ind_lambda):
		print('updateLineIntensityPlot2()')
		if (oneProfile is not None):
			'''
			# both oneProfile and x have shape of (n,), e.g. no specific column
			# we need to reshape them into shape of (n,1)
			oneProfile2 = np.reshape(oneProfile, (oneProfile.shape[0],1))
			x2 = np.reshape(x, (x.shape[0],1))
			# append columns, one after other
			oneProfile2 = np.append(x2, oneProfile2, 1) # 1 is for columns
			self.linePlot.set_data(oneProfile)
			'''

			# this works
			'''
			self.linePlot.set_data((x,oneProfile))
			self.linePlot.update()
			'''

			# see vispy InfiniteLineVisual to draw slice line

			data = np.random.rand(100,2) + 100
			# todo: add a member function to myVisPyWindow
			self.myVisPyWindow.linePlot.set_data(data)

			# already called by set_data
			#self.myVisPyWindow.linePlot.update()

			self.myVisPyWindow.linePlotWidget.view.camera.set_range()
			#self.myVisPyWindow.linePlot.view.camera.set_range()

		if (fit is not None):
			pass
			#self.fitPlot.setData(x, fit) # gaussian
		if (oneProfile is not None and not np.isnan(left_idx) and not np.isnan(right_idx)):
			left_y = oneProfile[left_idx]
			# cludge because left/right threshold detection has different y ...
			#right_y = oneProfile[right_idx]
			right_y = left_y
			xPnt = [left_idx, right_idx]
			yPnt = [left_y, right_y]
			#print('plot_pg() xPnt:', xPnt, 'yPnt:', yPnt)
			#self.fitPlot2.setData(xPnt, yPnt) # heuristic

	def updateLineIntensityPlot(self, x, oneProfile, fit=None, left_idx=np.nan, right_idx=np.nan): #, ind_lambda):
		"""
		Update the pyqt graph (top one) with a new line profile

		Parameters:
			oneProfile: ndarray of line intensity
		"""

		# new
		self.myPyQtGraphWidget.updateLinePlot(x, oneProfile, fit, left_idx, right_idx)

		'''
		print('updateLineIntensityPlot type(left_idx):', left_idx)
		print('updateLineIntensityPlot type(right_idx):', right_idx)
		'''
		if (oneProfile is not None):
			self.lineProfilePlot.setData(x, oneProfile)

		if (fit is not None):
			self.fitPlot.setData(x, fit) # gaussian
		if (oneProfile is not None and not np.isnan(left_idx) and not np.isnan(right_idx)):
			left_y = oneProfile[left_idx]
			# cludge because left/right threshold detection has different y ...
			#right_y = oneProfile[right_idx]
			right_y = left_y
			xPnt = [left_idx, right_idx]
			yPnt = [left_y, right_y]
			#print('plot_pg() xPnt:', xPnt, 'yPnt:', yPnt)
			self.fitPlot2.setData(xPnt, yPnt) # heuristic

if __name__ == '__main__':

	import sys

	with napari.gui_qt():
		# path to a tif file. Assuming it is 3D with dimensions of (slice, rows, cols)
		if len(sys.argv) == 2:
			path = sys.argv[1]
		else:
			path = '/Users/cudmore/box/data/bImpy-Data/high-k-video/HighK-aligned-8bit-short.tif'
		#path = '/Volumes/t3/20191105(Tie2Cre-GCaMP6f)/ISO_IN_500nM_8bit_cropped.tif'
		#path = '/Volumes/t3/20191105(Tie2Cre-GCaMP6f)/ISO_IN_500nM_8bit.tif'

		'''
		filename = os.path.basename(path)
		title = filename

		viewer = napari.Viewer(title=title)

		# add image as layer
		colormap = 'green'
		scale = (1,1,1) #(1,0.2,0.2)
		myImageLayer = viewer.add_image(
			#self.myStack.stack[0,:,:,:],
			path = path,
			colormap=colormap,
			scale=scale)#,
			#title=title)
		'''

		#tmp = myPyQtGraphWidget()

		# run the plugin
		#ShapeAnalysisPlugin(viewer, imageLayer=myImageLayer, imagePath=path)
		ShapeAnalysisPlugin(imagePath=path)
