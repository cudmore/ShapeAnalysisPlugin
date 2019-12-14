import sys
from vispy import scene
from vispy import app
import numpy as np

canvas = scene.SceneCanvas(keys='interactive')
canvas.size = 800, 600
canvas.show()

# Set up a viewbox to display the image with interactive pan/zoom
view = canvas.central_widget.add_view()

# Create the image
img_data = np.random.random((800,800, 3))
image = scene.visuals.Image(img_data, parent=view.scene)
view.camera.set_range()

# unsuccessfully tacked on the end to see if I can modify the figure.
# Does nothing.
img_data_new = np.zeros((800,800, 3))
#image = scene.visuals.Image(img_data_new, parent=view.scene)
image.set_data(img_data_new)
view.camera.set_range()

app.run() # run vispy event loop, does not return
