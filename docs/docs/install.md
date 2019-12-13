
This is a recipe for installing the Shape Analysis Plugin for [Napari][napari].

You can try to use our `install` script. This will only work on macOS and Linux.

```
./install
```

If that works, then run Napari with the plugin using

```
./run
```

If the above fails for whatever reason, use the following 3 steps...

### 1) Download or clone the code

**Option 1**, Download the repository as a .zip file and extract its contents

**Option 2**, Use git to clone the repository with

```
git clone https://github.com/cudmore/ShapeAnalysisPlugin.git
```

### 2) Install required Python packages

Assuming you have `Python 3.7.x`, `pip`, and `venv`

```
cd ShapeAnalysisPlugin

python3 -m venv env # create a virtual environment in folder 'env'
source env/bin/activate # activate the virtual environment

pip install -r requirements.txt
```

### 3) Run

```
cd shapeanalysisplugin
python3 ShapeAnalysisPlugin.py
```

[napari]: https://napari.org/
