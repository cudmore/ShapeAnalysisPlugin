import sys
import numpy as np
from PyQt5 import QtWidgets

import vispy
import vispy.plot as vp

class TryToUpdatePlot(QtWidgets.QWidget):
	def __init__(self):
		super(TryToUpdatePlot, self).__init__()
		self.initUI()

	def initUI(self):
		# vispy
		data = np.random.rand(100, 2) # random data
		fig = vp.Fig(size=(800, 600))
		line1 = fig[0, 0].plot(data=data)
		line2 = fig[1, 0].plot(data=data)

		# PyQt (with vispy fig.native)
		self.myHBoxLayout = QtWidgets.QHBoxLayout(self)
		self.myHBoxLayout.addWidget(QtWidgets.QPushButton('My Button'))
		self.myHBoxLayout.addWidget(fig.native)

		self.show()

		# update line1 plot with new data offset by 100
		newData = np.random.rand(100, 2) + 100
		# this call to set_data does not update the range of x/y axis
		# If I zoom out with mouse-wheel I can verify it is plotted
		line1.set_data(newData)

		# Is there something I can add here ???
		line1.update()
		#line1.view.camera.set_range()

if __name__ == '__main__':
	appQt = QtWidgets.QApplication(sys.argv)
	myClasss = TryToUpdatePlot()
	vispy.app.run() # run vispy event loop, does not return
