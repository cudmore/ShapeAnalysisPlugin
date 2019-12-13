
import os, sys

import numpy as np

from PyQt5 import QtGui, QtSql, QtCore, QtWidgets

import vispy.app
import vispy.plot as vp

# vispy
#canvas = vispy.app.Canvas()
fig = vp.Fig()
data = np.random.rand(100, 2)
fig[0, 0].plot(data=data)
fig[1, 0].plot(data=data)
fig[2, 0].plot(data=data)
fig[3, 0].plot(data=data)

# qt
w = QtWidgets.QMainWindow()
widget = QtWidgets.QWidget()
w.setCentralWidget(widget)
widget.setLayout(QtWidgets.QHBoxLayout())

widget.layout().addWidget(QtWidgets.QPushButton())
widget.layout().addWidget(fig.native)
#widget.layout().addWidget(canvas.native)

w.show()
vispy.app.run()
