This folder contains the markdown files and mkdocs.yml to configure user documentation with [MkDocs][mkdocs]. We are using the [Material][material] theme. Markdown files can be edited in any text editor or with a more visual interface using a program like [MacDown][macdown].

## Install

```
pip install mkdocs
```

```
pip install mkdocs-material
```

## Serving the documentation web pages locally

```
mkdocs build

# sometimes this
#mkdocs build --clean
```

You can then browse the web pages at a local address, something like

```
http://127.0.0.1:8000
```

## Pushing changes to github

```
mkdocs gh-deploy
```

[mkdocs]: https://www.mkdocs.org/
[material]: https://squidfunk.github.io/mkdocs-material/
[macdown]: https://macdown.uranusjr.com/
