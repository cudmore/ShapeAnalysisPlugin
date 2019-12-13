
import os, sys

import numpy as np

import napari

from PyQt5 import QtGui, QtSql, QtCore, QtWidgets

import vispy.app
import vispy.plot as vp


class bTest(QtWidgets.QWidget):
	def __init__(self):
		super(bTest, self).__init__()

		viewer = napari.Viewer(title='xxx')

		self.initUI()

		# vispy
		#canvas = vispy.app.Canvas()
		print('start __init__')

		if 0:
			self.fig = vp.Fig(size=(800, 600))
			data = np.random.rand(100, 2)
			self.fig[0, 0].plot(data=data)
			self.fig[1, 0].plot(data=data)
			self.fig[2, 0].plot(data=data)
			self.fig[3, 0].plot(data=data)

			# qt
			#w = QtWidgets.QMainWindow()
			widget = QtWidgets.QWidget()
			#w.setCentralWidget(widget)
			widget.setLayout(QtWidgets.QHBoxLayout())

			widget.layout().addWidget(QtWidgets.QPushButton('A Button'))
			widget.layout().addWidget(self.fig.native)
			#widget.layout().addWidget(canvas.native)

			#w.show()
			#widget.show()
			#vispy.app.run()

		print('end __init__')

	def initUI(self):
		# vispy
		#canvas = vispy.app.Canvas()
		print('start initUI')

		if 1:
			self.fig = vp.Fig(size=(800, 600), show=False)
			data = np.random.rand(100, 2)
			line1 = self.fig[0, 0].plot(data=data)
			self.fig[1, 0].plot(data=data)
			self.fig[2, 0].plot(data=data)
			self.fig[3, 0].plot(data=data)

		# qt
		#w = QtWidgets.QMainWindow()
		#widget = QtWidgets.QWidget()
		#w.setCentralWidget(widget)
		#widget.setLayout(QtWidgets.QHBoxLayout())

		self.myHBoxLayout = QtWidgets.QHBoxLayout(self)

		self.myHBoxLayout.addWidget(QtWidgets.QPushButton('A Button'))
		self.myHBoxLayout.addWidget(self.fig.native)
		#widget.layout().addWidget(QtWidgets.QPushButton('A Button'))
		#widget.layout().addWidget(self.fig.native)
		#widget.layout().addWidget(canvas.native)

		#w.show()
		#widget.show()
		#vispy.app.run()

		self.show()

		data = np.random.rand(100, 2) + 100
		line1.set_data(data)

if __name__ == '__main__':
	with napari.gui_qt():
		#viewer = napari.Viewer(title='xxx')
		print(1)
		test = bTest()
		print('exiting')
