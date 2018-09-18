import shutil, os
import Tkinter #import Tk
import tkFileDialog
import tkMessageBox

import fnmatch

sourceFiles = []
targetFiles = []

sourceDir = ""
targetDir = ""
newFilesDir = ""
pattern = '*.wav'


def askUserForImportDirectory():
    root = Tkinter.Tk()
    root.withdraw()
    root.update()
    dir = tkFileDialog.askdirectory(title = "Hello pick a folder")
    root.update()
    root.destroy()
    return dir
    # print(MyComponent.INPUT_audioFilePath)


def setupSourceAudioFileList(path):
    # print("Setting up list of audio files")
    filelist = []


    for root, dirs, files in os.walk(path):
        # for file in os.listdir(path):
        for filename in fnmatch.filter(files, pattern):
            absFilePath = os.path.abspath(os.path.join(root, filename))
            filelist.append(absFilePath)
    return filelist

################################################################

countFilesReplaced = 0
countNewFiles = 0

tkMessageBox.showinfo("Choose Directories", "Choose source file directory")
sourceDir = askUserForImportDirectory()

tkMessageBox.showinfo("Choose Directories", "Choose target file directory")
targetDir = askUserForImportDirectory()

tkMessageBox.showinfo("Choose Directories", "Choose new files directory")
newFilesDir = askUserForImportDirectory()

sourceFiles = setupSourceAudioFileList(sourceDir)
targetFiles = setupSourceAudioFileList(targetDir)

for file in sourceFiles:
    filebase = os.path.basename(file)
    found = False
    for targetfile in targetFiles:
        if filebase == os.path.basename(targetfile):
            shutil.copy(os.path.abspath(file), os.path.abspath(targetfile))
            found = True
            countFilesReplaced += 1
            break
    if found == False:
        shutil.copy2(os.path.abspath(file), os.path.abspath(newFilesDir))
        countNewFiles += 1

tkMessageBox.showinfo("Results", "Replaced "+str(countFilesReplaced)+" files. Copied "+str(countNewFiles)+" new files.")