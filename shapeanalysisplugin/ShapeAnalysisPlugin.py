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

import scipy.ndimage

import napari

#import vispy.app
#import vispy.plot as vp

from ShapeAnalysis import ShapeAnalysis # backend analysis
from myPyQtGraphWidget import myPyQtGraphWidget

class ShapeAnalysisPlugin:
	"""
	handle interface of one shape roi at a time

	uses ShapeAnalysis for back end analysis
	"""

	def __init__(self, imagePath=None):
		"""
		Parameters:
			imagePath : full path to .tif file

		Assuming:
			imageLayer.data is (slices, rows, col)
		"""

		self.path = imagePath

		title = '' # window title
		if imagePath is not None:
			title = os.path.basename(imagePath)

		self.napariViewer = napari.Viewer(title=title)

		# how do we set position and size of viewer?
		# in Qt it is self.setGeometery(x,y,w,h)

		# add image as layer
		colormap = 'green'
		scale = (1,1,1) #(1,0.2,0.2)
		self.myImageLayer = self.napariViewer.add_image(
			#self.myStack.stack[0,:,:,:],
			path = path,
			colormap=colormap,
			scale=scale)

		self.sliceNum = 0

		self.filterImage() # filter the raw image for analysis

		# analysis back-end to calculate diameter of lines and mean intensity of rectangles
		# this uses multiprocessing
		self.analysis = ShapeAnalysis(self.imageData) # self.imageData is a property

		#
		# make an empty shape layer
		self.shapeLayer = self.napariViewer.add_shapes(
			name=self.myImageLayer.name + '_shapes',
		)
		self.shapeLayer.mode = 'select' #'select'
		self.shapeLayer.metadata = [] # we need to append/pop from this as we create/delete shapes

		# instantiate the main window to hold all shape analysis plots
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

		self.mouseBindings() # map key strokes to function calls
		self.keyboardBindings() # map mouse down/drag to function calls

		# load any analysis files for this .tif file
		self.load()

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
			print('=== ShapeAnalysisWidget Help')
			print('l:               Create new line shape')
			print('r:               Create new rectangle shape')
			print('Delete:          Delete selected shape')
			print('u:               Update analysis on selected shape')
			print('Command+Shift+L: Load h5f file (prompt user for file)')
			print('Command+l:       Load default h5f file (each .tif has corresponding h5f file)')
			print('Command+s:       Save default h5f file (each .tif has corresponding h5f file)')

		@self.shapeLayer.bind_key('l', overwrite=True)
		def shape_user_keyboard_l(layer):
			""" create/add a new line shape, user should not use napari icon to create shape """
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
		def user_keyboard_a(viewer):
			""" analyze selected shape """
			print('=== user_keyboard_u')
			self.updateAnalysis()

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
		print('filterImage() is creating gaussian filtered image:', self.myImageLayer.data.shape)
		startTime = time.time()
		self.filtered = scipy.ndimage.gaussian_filter(self.myImageLayer.data, sigma=1)
		stopTime = time.time()
		print('   took', round(stopTime-startTime,2), 'seconds')

	def _deleteShape(self):
		""" Delete selected shape, from napari and from myPyQtGraphWidget """

		shapeType, index, data = self._getSelectedShape()

		print('_deleteShape()')
		print('   shapeType:', shapeType)
		print('   index:', index) # absolute shape index
		print('   data:', data)

		# (1)
		if shapeType == 'rectangle':
			self.myPyQtGraphWidget.shape_delete(index)

		# delete from napari
		# order matters, this has to be after (1) above
		self.shapeLayer.remove_selected() # remove from napari
		# we are managing metadata list (append on new shape, pop on delete)
		self.shapeLayer.metadata.pop(index)

		# update plots
		self.updatePlots(updatePolygons=True) #refresh plots
		#self.myPyQtGraphWidget.plotAllPolygon(None)

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
				print('   loading name:', name)
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

		# create a shape from what we loaded
		print('   Appending', len(linesList), 'loaded shapes to shapes layer')

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
		self.updatePlots(updatePolygons=True)
		#self.myPyQtGraphWidget.plotAllPolygon(None)

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

		#type, index, dict = self._getSelectedShape()

		'''
		print('ShapeAnalysisPlugin.myMouseDown_Shape()', layer, event.type)
		print('   type:', type)
		print('   index:', index)
		print('   dict:', dict) # (type, index, dict)
		'''

		self.updatePlots()

	def lineShapeChange_callback(self, layer, event):
		"""
		Callback for when user clicks+drags to resize a line shape.

		Responding to @self.shapeLayer.mouse_drag_callbacks

		update pg plots with line intensity profile

		get one selected line from list(self.shapeLayer.selected_data)
		"""

		shapeType, index, data = self._getSelectedShape()
		if shapeType == 'line':
			self.updateLines(self.sliceNum, data)

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
		if (event.axis == 0):
			# todo: not sure if this if foolproof
			self.sliceNum = self.napariViewer.dims.indices[0]

			self.myPyQtGraphWidget.updateVerticalSliceLines(self.sliceNum)

			# todo: this does not feel right ... fix this !!!
			shapeType, index, data = self._getSelectedShape()
			if shapeType == 'line':
				self.updateLines(self.sliceNum, data)

	def updatePlots(self, updatePolygons=False):
		"""
		update plots based on current selection

		todo: The logic here is all screwed up. We need to update even if there is not a selection !!!!

		This needs to update (1) a line based on selection and (2) all rectangle shapes/roi, regardless of selection
		"""

		print('bShapeAnalysisPlugin.updatePlots()')

		shapeType, index, data = self._getSelectedShape()

		# on delete, these will all be None
		print('   shapeType:', shapeType)
		print('   index:', index)

		# in the end just use this
		self.myPyQtGraphWidget.updateShapeSelection(index)

		if updatePolygons:
			self.myPyQtGraphWidget.plotAllPolygon(index)

	def updateAnalysis(self):
		"""
		Update the analysis of the currently selected shape
		"""
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
		#self.myPyQtGraphWidget.updateShapeSelection(index)

	def updateStackLineProfile(self):
		"""
		generate a line profile for each image in a stack/timeseries

		data: two points that make the line
		"""
		shapeType, index, data = self._getSelectedShape()

		src = data[0]
		dst = data[1]
		print('updateStackLineProfile() src:', src, 'dst:', dst)
		x, lineKymograph, lineDiameter = self.analysis.stackLineProfile(src, dst)

		self.shapeLayer.metadata[index]['lineDiameter'] = lineDiameter
		self.shapeLayer.metadata[index]['lineKymograph'] = lineKymograph

		self.updatePlots()

	def updateStackPolygon(self, index=None):
		"""
		data is a list of points specifying vertices of a polygon
		a rectangle is just a polygon with 4 evenly spaces vertices
		"""
		print('bShapeAnalysisPlugin.updateStackPolygon() index:', index)

		shapeType, index, data = self._getSelectedShape()

		# back-end analysis
		theMin, theMax, theMean = self.analysis.stackPolygonAnalysis(data)

		if theMin is None:
			return

		# store in shape metadata
		self.shapeLayer.metadata[index]['polygonMean'] = theMean

		# plot
		self.updatePlots(updatePolygons=True)

	def updateVerticalSliceLines(self, sliceNum):
		"""
		Set vertical line indicating current slice
		"""
		for line in self.sliceLinesList:
			line.setValue(sliceNum)

	def updateLines(self, sliceNum, data):
		"""
		data: two points that make the line
		"""
		src = data[0]
		dst = data[1]
		print('bShapeAnalysisWidget.updateLines() sliceNum:', sliceNum, 'src:', src, 'dst:', dst)
		# this can fail ???
		x, lineProfile, yFit, fwhm, leftIdx, rightIdx = self.analysis.lineProfile(sliceNum, src, dst, linewidth=1, doFit=True)

		self.updateLineIntensityPlot(x, lineProfile, yFit, leftIdx, rightIdx)

	def updateLineIntensityPlot(self, x, oneProfile, fit=None, left_idx=np.nan, right_idx=np.nan): #, ind_lambda):
		"""
		Update the pyqt graph (top one) with a new line profile

		Parameters:
			oneProfile: ndarray of line intensity
		"""

		# new
		self.myPyQtGraphWidget.updateLinePlot(x, oneProfile, fit, left_idx, right_idx)

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

		# run the plugin
		ShapeAnalysisPlugin(imagePath=path)
