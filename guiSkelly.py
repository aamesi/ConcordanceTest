#-------------------------------------------------------------------------------
# Name:        guiSkeleton.py
# Purpose:      Quick and easy low level api for tkinter gui programming. CUstom use
#
# Author:      Azuveike
#
# Created:     14/03/2015
# Copyright:   (c) Azuveike 2015
# Licence:     <your licence>
#-------------------------------------------------------------------------------
import tkinter
from tkinter import filedialog
from tkinter import *

#register the function

def loadSkelly():
    root=tkinter.Tk()
    return root

def getfile(root, filename):
    """Open a file browser dialog. Expects a tk root/master window. Returns file name"""
    root.filename =  filedialog.askopenfilename(initialdir = "C:/",title = "choose your file",filetypes = (("csv files","*.csv"),("all files","*.*")))
    filename.append(root.filename)
    #print(filename)
    return root.filename

def savefile(root,filelist):
    """Currently hardcoded for csv files"""
    file_opt = options = {}
    options['filetypes'] = [('all files', '.*'), ('csv files', '.csv')]
    options['initialfile'] = 'matrix_out.csv'
    options['parent'] = root
    savefile = filedialog.asksaveasfilename(**file_opt)

    if savefile:
        filelist.append(savefile)

def addLabel(root,message, row_slot=None,column_slot=None):
    """Takes a root window and message.Adds a label to a tk window and returns a reference to it"""
    var=tkinter.StringVar()
    label = tkinter.Label(root, text=message,textvariable=var)
    var.set(message)
    if row_slot is not None: # check positional arguments
        label.grid(row=row_slot) # set the grid slot
    if column_slot is not None: # same as above
        label.grid(column=column_slot)
    #label.pack
    return var

def addChkbtn(root,message,row_slot=None, column_slot=None):
    var = tkinter.IntVar()
    chkbtn= tkinter.Checkbutton(root, text=message,variable=var)
    if row_slot is not None: # check positional arguments
        chkbtn.grid(row=row_slot) # set the grid slot
    if column_slot is not None: # same as above
        chkbtn.grid(column=column_slot)
    #label.pack
    return var

    pass

def addDefaultButton(root,label,function = None,row_slot=None,column_slot=None):
    button = tkinter.Button(root, text=label, fg="black",command= function)
    #button.pack(side=tkinter.LEFT)
    if row_slot is not None: # check positional arguments
        button.grid(row=row_slot) # set the grid slot
    if column_slot is not None: # same as above
        button.grid(column=column_slot)
    return button
    pass

def addButton(root,label,function = None,arguments=None,row_slot=None,column_slot=None):
    """Takes a root window, a label, and a function(lambda) and registers a new button with the function event"""

    button = tkinter.Button(root, text=label, fg="black",command= lambda: function(root,arguments))
    #button.pack(side=tkinter.LEFT)
    if row_slot is not None: # check positional arguments
        button.grid(row=row_slot) # set the grid slot
    if column_slot is not None: # same as above
        button.grid(column=column_slot)
    return button
    pass



def setTitle(root,title):
    root.title = title # set the title. No need to return anything

def addEntry(root,row_slot=None,column_slot=None):
    """Adds a textbox to the window and returns a reference to it"""
    textbox = tkinter.Entry(root) # register the textbox with the root window
    if row_slot is not None: # check positional arguments
        textbox.grid(row=row_slot) # set the grid slot
    if column_slot is not None: # same as above
        textbox.grid(column=column_slot)
        #textbox.pack()
    return textbox # return the textbox
    pass

def addListBox(root,row_slot=None,column_slot=None):
    #frame = Frame(root)

    listbox = tkinter.Listbox()
    #scrollbar.config(command=listbox.yview)
    #scrollbar.pack(side=RIGHT, fill=Y)
    if row_slot is not None: # check positional arguments
        listbox.grid(row=row_slot) # set the grid slot
    if column_slot is not None: # same as above
        listbox.grid(column=column_slot)
        #textbox.pack()
    return listbox # return the textbox

def  listCallBackAdd(root,label,function = None,arguments=None,row_slot=None,column_slot=None):
    """Attach callback to list using button. Binds lb and button.Arg1=string"""
    button = tkinter.Button(root, text=label, fg="black",command= lambda: function(END,arguments))
    #button.pack(side=tkinter.LEFT)
    if row_slot is not None: # check positional arguments
        button.grid(row=row_slot) # set the grid slot
    if column_slot is not None: # same as above
        button.grid(column=column_slot)
    return button
    pass





def main():
    root = loadSkelly()

    text1 = addEntry(root,0,1)
    text2 = addEntry(root,0,2)
    listbox1 = addListBox(root,3,3)
    button = listCallBackAdd(root,"Add Pattern",listbox1.insert,text1.get(),0,3)


    for items in listbox1.get(0,END): # loop through the listbox
        print(items)

    root.mainloop()

    pass

if __name__ == '__main__':
    main()
