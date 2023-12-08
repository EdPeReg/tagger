# Description

This is just a little tagger and backup program, it will tag your media files and back up them to a specific folder.

Basically you provide as first argument the folder you want to be analized, it will find all the media files given
that path with that date, it will tag them and them move them.

You will have the opportunity to:

- Tag the file
- Remove it if you want
- Skip the file
- Move the tagged files to another folder

It will open the default application to visualize the file, in that way you will know which file you are working.

Work in progress :)

# NOTE

This is tested on Fedora 39 with Python 3.12.0, it is intended to be used on Linux, that's why it uses Linux commands, probably because of this it won't work on Windows.
Also it uses _exiftool_ to tag the photos, if the tool is not installed it won't work, _exiftool_ is a dependency.

exiftool also is available on windows: [exiftool for windows](https://exiftool.org/install.html)

# How to use it

```python
python main.py ~/Documents 2023-11-25
```

