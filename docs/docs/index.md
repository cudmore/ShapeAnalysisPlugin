Welcome. This is the user documentation for the Napari shape analysis plugin.

## What it does and why it is great ...

 - Using the [Napari viewer][napari], any number of shapes/ROIs can be created directly on top of multi-dimensional images.
 - Shapes/ROIs are easily analyzed to extract parameters and plot the results.
 - Shapes/ROIs and their analysis can be saved and then loaded again.
 - Once shapes/ROIs are analyzed with the graphical user interface (GUI), additional analysis can be perfromed with super simple pYthon scripts.
 - Analysis is implemented to be fast by utilizing all CPU cores with Python's [multiprocessing libraries][python-multiprocessing].
 - As we develop this, we are in close contact with the Napari developers at [The Chan/Zuckerberg Initiative][czi] who are consistently rolling out exciting new features and cutting edge improvements.

## Example screenshot

![plugin-screenshot-gif](img/shape-analysis-plugin.gif)

On the left is the Napari viewer with a time-series of images, basically a video recording. The Napari viewer has two shapes, a line (blue) and a rectangle (orange). Shapes can easily be created, deleted, and edited using the Napari interface.

On the right is the Shape Analysis Plugin interface with four plots. The top plot is showing the line intensity profile along the line shape (white), a gaussian fit (red), and a best guess of the diameter of the line intensity profile (blue). The second plot is showing the best guess of the diameter for each frame in the time-series. The third plot is an image where the line intensity profile of each frame in the time-seriesis vertical. The fourth plot is showing the mean image intensity inside the rectangular shape/ROI, one value per image frame in the time-series.

As the user drags the slider to scroll through image frames in the time-series, all the plots are updated. For the bottom three plots, the currently viwed image frame is denoted by a vertical white/yellow bar.

<!--

**Details...** The image is a video recording of a [sinoatrial node][sinoatrial-node] artery with [GCaMP][gcamp] expressed in [endothelial cells][endothelial-cells]. Around frame 800 there is a spontaneous Ca++ event within the rectangular shape. Around frame 1300, we are applying high K+ to constrict the vessel. This can be seen as both a decrease in the diameter (second plot) accompanied by an increase in Ca++.

**Why...** We are using this plugin to examine the response of arteries, both in their constriction and Ca++ signalling in different disease states including Alzheimer's disease, hypertension, diabetes, and stroke.

[sinoatrial-node]: https://en.wikipedia.org/wiki/Sinoatrial_node
[gcamp]: https://en.wikipedia.org/wiki/GCaMP
[endothelial-cells]: https://en.wikipedia.org/wiki/Endothelium

-->

[napari]: https://napari.org/
[napari github]: https://github.com/napari/napari
[python-multiprocessing]: https://docs.python.org/2/library/multiprocessing.html
[czi]: https://chanzuckerberg.com/
