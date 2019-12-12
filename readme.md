## Introduction

This is a [Napari][napari] plugin that is designed to analyze shapes, better known as regions of interest (ROIs).

If you are an end user, please see our [user friendly documentation](http://blog.cudmore.io/ShapeAnalysisPlugin/).

## Disclaimer

We are developing this code in the open but the project is still in an early alpha stage and there will be breaking changes with each release. Please follow along as we develop this exciting new software and feel free to try it out and contribute your ideas and if possible your own code.

## Screenshot

![plugin-screenshot-gif](img/shape-analysis-plugin.gif)


## How to install

### 1) Download the code

**Option 1**, Download the repository as a .zip file and extract its contents

**Option 2**, Use git to clone the repository with

```
git clone https://github.com/napari/napari.git
```

### 2) Install on your computer

Assuming you have `Python 3.7.x`, `pip`, and `venv`

```
cd ShapeAnalysisPlugin
pip install -r requirements.txt
```

### 3) Run

```
cd ShapeAnalysisPlugin
python3 ShapeAnalysisPlugin.py
```

## Interface

The Shape Analysis Plugin uses keyboard commands for its user interaction. We will improve this in the near future. 

```
l: Create new line shape (l as in Larry)
r: Create new rectangle shape
Delete: Delete selected shape
u: Update analysis on selected shape
Command+Shift+L: Load h5f file (prompt user for file)
Command+l: Load default h5f file (each .tif has corresponding h5f file)
Command+s: Save default h5f file (each .tif has corresponding h5f file)
```





[napari]: https://napari.org/
[napari github]: https://github.com/napari/napari
[python-multiprocessing]: https://docs.python.org/2/library/multiprocessing.html
[sinoatrial-node]: https://en.wikipedia.org/wiki/Sinoatrial_node
[gcamp]: https://en.wikipedia.org/wiki/GCaMP
[endothelial-cells]: https://en.wikipedia.org/wiki/Endothelium
[czi]: https://chanzuckerberg.com/