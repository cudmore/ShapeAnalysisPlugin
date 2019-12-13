import numpy as np
#import napari
from PyQt5 import QtWidgets
import vispy.plot as vp

class TryToUpdatePlot(QtWidgets.QWidget):
	def __init__(self):
		super(TryToUpdatePlot, self).__init__()

		#viewer = napari.Viewer()

		self.initUI()

	def initUI(self):
		fig = vp.Fig(size=(800, 600), show=False)

		# random data
		data = np.random.rand(100, 2)

		line1 = fig[0, 0].plot(data=data)
		line2 = fig[1, 0].plot(data=data)

		self.myHBoxLayout = QtWidgets.QHBoxLayout(self)

		self.myHBoxLayout.addWidget(QtWidgets.QPushButton('A Button'))
		self.myHBoxLayout.addWidget(fig.native)

		self.show()

		# update line1 plot with new data offset by 100
		data = np.random.rand(100, 2) + 100
		# this call to set_data does not update the range of x/y axis
		line1.set_data(data)

		# Is there something I can add here ???
		#line1.update()
		#line1.view.camera.set_range()

if __name__ == '__main__':
	#with napari.gui_qt():
	if 1:
		test = TryToUpdatePlot()
