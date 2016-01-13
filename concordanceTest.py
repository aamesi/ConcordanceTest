#

from collections import namedtuple
from collections import OrderedDict
from operator import itemgetter
import threading
from multiprocessing.pool import ThreadPool
import time
import csv
import guiSkelly
import pickle
from pickle import Pickler
from scipy import stats
from scipy.stats import stats
import os
import sys
import logging
import tkinter.ttk
from tkinter import *
from tkinter import messagebox
import time
from threading import Thread
import traceback

#read
tolerance = 0.00001;# select a tolerance of 5 decimal places
#similar to a struct. Named tuple of floats
Data_vals = namedtuple("Data_vals", "onset_beats,duration_beats,channel,pitch,velocity,onset_sec,duration_sec,piece,loc_list")
Loc_conc = namedtuple("Loc_conc", "concordance_pattern,location,hard_location")
matrix_partition_counter=200000000# will set aside 200MB for the temporary matrix storage. Used in process overlap/

"""Partiton counter limits the amount of memory for the count value table"""
partition_counter = 4500000

INT_SIZE = sys.getsizeof(int())

FLOAT_SIZE = sys.getsizeof(float())

LIST_SIZE= sys.getsizeof(list())


def compFloat(f1,f2):
    """This function takes two floats,compares them to a tolerance and returns a boolean if they are equal"""
    #first check if both are integers
    if f1.is_integer() and f2.is_integer():
        if int(f1)==int(f2):
            return True
        else:
            return False

    if abs(f1-f2) < tolerance and abs(f2-f1) < tolerance:
        return True
    return False


class ConcordanceApp:
    """The wrapper for the application. all methods are called through this class. gui is contained within as well"""
    def __init__(self):
        """Initializer class"""

        self.openLoc=[]#openfile location
        self.saveLoc = []#savefile loc
        self.track = None # track level
        self.beats =None# interval between beats
        self.conc_length = None # n gram length
        self.total_counter=0
        self.base_store_file = "overlap" # name of overlap disk file
        self.base_matrix_file = "matrix" # name of matrix disk file
        self.p_matrix_file = "pmatrix"  # name of pmatrix file
        self.countvaluetable = dict()
        self.basstable = dict()
        self.melodytable = dict()

        """These variables will be linked to tkinter checkboxes that determine the flow of the program.phase 1,2,3"""
        self.chkp1=None
        self.chkp2=None
        self.chkp3 = None
        """These variables are linked to tkinter labels to update the program state periodically"""
        self.out1=None
        self.out2=None
        self.out3=None

        self.winref=None # a reference to the gui
        self.root=None

        """These variables keep track of the number of files we write to the disk temporarily to not run out of memory"""
        self.file_counter=0 # keeps track of our current file counter. used in phase 2
        self.matrix_file_counter=0 # keepts track of our matrix file counter.used in phase 2
        self.pmatrix_file_counter=0 # pmatrix file counter. used in phase 3
        self.logger = None
        """These variables are used in phase 2 and 3"""
        self.local_countvaluetable= dict()
        #self.local_total_counter=0
        self.local_basstable = dict() # dictionary of bass intersection counters
        self.local_melodytable = dict()# dictionary of melody intersection counters
        self.thread_tk=None#our 2nd thread for the additional gui
        """these are used for the querys"""
        self.query_range = None# guiSkelly.addEntry(self.root,1,4)
        self.pitch_range = None# guiSkelly.addEntry(self.root,1,4)
        self.query_box = None
        self.querystart = None
        self.querylist = None


    def initialize(self):
        """Initialize a gui and class varaibles for the program"""

        #Set up the labels on the gui. requires a root window, label description,row position, column position
        self.root = guiSkelly.loadSkelly()
        self.root.title("Schema Discovery and Search")
        labelsingletrack= guiSkelly.addLabel(self.root,"Single Stream Analysis Track",0,1)
        labelbeat= guiSkelly.addLabel(self.root,"Choose an (IOI) or Beat-level to Analyze.",1,1)
        label_ingram=guiSkelly.addLabel(self.root,"Choose n-gram length",2,1)
        label_qrange = guiSkelly.addLabel(self.root, "Maximum displacement (beats)",9,2)
        label_prange = guiSkelly.addLabel(self.root,"Vertical interval",10,2)
        label_line = guiSkelly.addLabel(self.root,"Open an NMAT file and \n Use the Schema Discovery Widget (Right) \n OR \n Input a specific pattern (Below)" ,3,0)
        label_line = guiSkelly.addLabel(self.root,"________________________________" ,4,0)
        label_line = guiSkelly.addLabel(self.root,"        " ,0,4)
        label_query = guiSkelly.addLabel(self.root,"Input pattern." ,8,1)


        #Set up textboxes on the gui. requires a root window, row position, column position Starting with 0 for initial pitch eg. (0,-1,-3;0,1,2) searches for the fa me re, ti la sol, etc. spaced one quarter note apart. Enter Upper voice then lower voice
        self.track = guiSkelly.addEntry(self.root,0,2)
        self.beats = guiSkelly.addEntry(self.root,1,2)
        self.conc_length = guiSkelly.addEntry(self.root,2,2)
        self.query_range =  guiSkelly.addEntry(self.root,9,3)
        self.pitch_range =  guiSkelly.addEntry(self.root,10,3)
        self.querylist = guiSkelly.addListBox(self.root,13,1)


        #Set up buttons on the gui. requires root window, button name, function to call on click,variable to save results, row position,column position
        button = guiSkelly.addButton(self.root,"Open File",guiSkelly.getfile,self.openLoc,0)
        button2 = guiSkelly.addButton(self.root,"Save Concordance and Overlap Files",guiSkelly.savefile,self.saveLoc,0,5)
        button3 = guiSkelly.addButton(self.root,"Start Discovery",self.startProgram,self.root,1,5)
        button4 = guiSkelly.addDefaultButton(self.root,"Add Pattern",self.addListEntry,10,1)
        buttondelete = guiSkelly.addDefaultButton(self.root,"Remove Patterns", self.removeListEntry,14,1)
        button5 = guiSkelly.addDefaultButton(self.root, "Start Search",self.phaseIV,13,5)

        #Set up check buttons on the gui. Requires root window, checkbutton tag, row posiition, column position
        self.chkp1 = guiSkelly.addChkbtn(self.root,"Construct Concordances" ,3,1)
        self.chkp2 = guiSkelly.addChkbtn(self.root,"Construct Overlap matrix",3,2)
        self.chkp3 = guiSkelly.addChkbtn(self.root,"Perform Fisher Exact Test",3,3)
        self.query_box = guiSkelly.addEntry(self.root,9,1)
        self.winref=tkinter.Toplevel(self.root)#make a 2nd window
        self.nmat = None

        #Set up labels  and text on the  2nd gui. Requires 2nd root window, label tag, row,position.
        self.out1 = guiSkelly.addLabel(self.winref,"Ready                           ",4,2)
        self.out2 = guiSkelly.addLabel(self.winref,"Ready                           ",5,2)
        self.out3 = guiSkelly.addLabel(self.winref,"------------------------                           ",6,2)
        self.winref.title("Concordance6(Working)")
        self.winref.geometry("400x70")
        self.winref.withdraw()
        self.winref.protocol("WM_DELETE_WINDOW",self.onExit)

        # NOW initialize the logger
        self.logger = logging.getLogger('concordancesv7b')
        hdlr = logging.FileHandler('concordancesv7b.log')
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        hdlr.setFormatter(formatter)
        self.logger.addHandler(hdlr)
        self.logger.setLevel(logging.WARNING)

    def addListEntry(self):
        """Adds an item into the list box"""
        self.querylist.insert(END,self.query_box.get())

    def removeListEntry(self):
        """Removes selected items from the list box"""
        items = self.querylist.curselection()
        pos = 0
        for i in items :
            idx = int(i) - pos
            self.querylist.delete( idx,idx )
            pos = pos + 1

    def errorRespond(self,e):
        self.logger.error(e)


    def loadData(self,file_in="giantnotematrix.csv"):
        """Read a matrix in string form and convert it into a list of tuple"""
        self.out2.set("Reading in " + file_in)
        list_dataVals = []
        counter=0
        #Matrix =  list(namedtuple)
        try:
            with open(file_in,newline='') as csvfile:
                spamreader = csv.reader(csvfile)
                for splits in spamreader:
                    #splits = line.split()
                    onset = float(splits[0])
                    #print(onset)
                    duration = float(splits[1])
                    channel=int(splits[2])
                    pitch = float(splits[3])
                    velocity = float(splits[4])
                    onset_sec = float(splits[5])
                    duration_sec=float(splits[6])
                    piece=float(splits[7])
                    next_row = Data_vals(onset,duration,channel,pitch,velocity,onset_sec,duration_sec,piece,list())
                    list_dataVals.append(next_row)
                    counter+=1
                    #if counter>10000:
                    #    break
        except Exception as e:
            self.out3.set("Error reading in file")
            print(e)
            #self.errorRespond(e)
            tb = traceback.format_exc()
            print(tb)
            self.errorRespond(tb)
        self.nmat = list_dataVals

        return list_dataVals
    #0---------------------------end LOADDATA-------------------------#


    def processRow(self,n_mat,position,beat_level,track,interval):
        """Takes a matrix(list of tuples), position(int), and a beat_level(skip) and returns a concordance(list) if one is found"""
        #check next entrys onset to see if valid.
     #   print("process row")
        """If we check the next row and the difference between beat levels is greater than the beat level, exit the loop and return null"""

        last_row = n_mat[position]# get the row we're processing
        """Make sure this row should be analyzed by checking its channel against the track level"""
        if track != last_row.channel:
         #       print("not same channel")
                return None
        max_beats= (interval *beat_level)- beat_level# th maximum beat to analyze
        """Initialize our concordance list, and location list while also setting the initial pitch"""
        location = []# location where it starts

        initial_pitch= last_row.pitch
        initial_beat = last_row.onset_beats
        initial_loc = str(last_row.onset_beats)
        current_piece =n_mat[position].piece
        """concordance is relative to the starting pitch, so set the first pattern to 0"""
        concordance = list()
        list_of_concordances = list() # our list of levels of concordances. length is gram interval

        """initialize the lists"""
        for x in range(0,interval):
            list_of_concordances.append(list())
        list_of_concordances[0].append(0)
        counter = 1 # this is our layer level in the lists of lists

        for x in range(position+1,len(n_mat)):
            current_row = n_mat[x]

            if track!= current_row.channel: # if not same ctrack, do not process
                continue
            if current_piece != current_row.piece:#misaligned pieces
                break
            if current_row.onset_beats > initial_beat + max_beats and not compFloat(current_row.onset_beats,initial_beat + (counter*beat_level)) :# if we are out of range, stop the loop

                break
            """Look for a match"""
            if compFloat(current_row.onset_beats,initial_beat + (counter*beat_level)):

                list_of_concordances[counter].append(int(current_row.pitch-initial_pitch))
            elif current_row.onset_beats > initial_beat + float(counter*beat_level):#check if we are outside the current range

                counter+=1 #increment the counter """ check if we stepped over the current boundary"""
                if compFloat(current_row.onset_beats,initial_beat + (counter*beat_level)):
                    #now process the row
                    list_of_concordances[counter].append(int(current_row.pitch-initial_pitch))




        """Now verify we have solid lists"""

        """If we have a 0 length list, return none"""
        for items in list_of_concordances:
            if len(items)==0:

                return None


        top_layer = list()#list that will eventually contain all our concordances
        top_layer.append(0)
        output = list()# our list that will contain  our temp concordances
        layer_count=1
        loc_data=list()
        while layer_count < interval :
            for top_item in top_layer:
                for next_item in list_of_concordances[layer_count]:
                    #append a tuple
                    output.append(str(top_item) + "," + str(next_item))
            top_layer=output
            layer_count+=1
            output=[]

        """Now we have X amount of strings in a list that each correspond to a concordance """



        total = len(top_layer)
        for x in range(0,total):
            concordance.append(list())
            location.append(list())
            loc_data.append(list())
            location.append(list())
            location[x].append(initial_loc)
        x=0
        for item in top_layer:#loop through our lists of strings

            for item2 in item.split(","): # split the string into individual items
                concordance[x].append(int(item2))
            x+=1





        """ Prep the location list"""

        for x in range(0,total):
            for y in concordance[x]: # now add the concordance items in order

                location[x].append(str(y))

        y=0
        for locs in location:

            if y< len(loc_data):
                if len(locs)>0:
                    loc_data[y]= ",".join(locs)
            else:# RESUME HERE
                break
            y+=1



        our_row=Loc_conc(concordance,loc_data, str(position+1))# make a tuple to return
        return our_row
    #0---------------------------end PROCESSROW-------------------------#


    def processMatrix(self,n_mat,beat_level,track,interval):
        """@params list, beat level(int) and track(int). returns a tuple.(dictionary,list)"""

        try:
            concorances = list()
            dict_list = dict()# key:concordance string, value=location list
            static_dict_list = dict() # location list relative to the initial csvfile
            matrix_length = len(n_mat)

            for i in range(0,len(n_mat)):#loop through each row and process by calling processRow
                self.out2.set("Analyzing row " + str(i+1) + "of" + str(matrix_length))
                nextEntry = self.processRow(n_mat,i,beat_level,track,interval)#proces the row
                if nextEntry is not None:# if we have a concordance, append it to the return value
                    concorances.append(nextEntry)
                    for x in range(0,len(nextEntry[0])):#loop through our lists of lists
                        if len(nextEntry[0][x]) >0:
                            this_row = ''.join(str(nextEntry[0][x])).replace('[','').replace(']','')
                            if this_row in dict_list:
                                dict_list[this_row]+= "," + ((nextEntry[1][x])).split(",")[0]#append the location to our location list
                                static_dict_list[this_row]+= ","+ (nextEntry[2])#append relative location list
                            else: #make new entries in our dictionaries
                                dict_list[this_row] = (nextEntry[1][x]).split(",")[0]#add the location which is in the first slot of loc_Data
                                static_dict_list[this_row] =  nextEntry[2]
                else:
                    pass
        except Exception as e:
            self.errorRespond(e)# respond to the error and exit the progfrM


        return (concorances,dict_list,static_dict_list)
        #0---------------------------end PROCESSMATRIX-------------------------#

    def buildConcordance(self,concordances):
        """@params tuple of dict, returns tuple of more dicts"""
        try:
            self.out2.set("Building concordance graph")
            finalDict= dict()# dict to return
            final_locDict = list()
            for i in concordances[0]: # loop through the concordances

                for x in i[0]: # for each concordance in our list of concordance
                    if len(x)>0:

                        this_row = ', '.join(str(i) for i in x).replace('[','').replace(']','') # generate a list of strings from a list of ints

                        if  this_row in finalDict: #if its already in the dictionary, increase the frequency
                            finalDict[this_row] +=1
                        else:
                            finalDict[this_row] = 1
                        for y in range(0,len(i[1])):
                            final_locDict.append(i[1][y])#add the location string


            lastdict = OrderedDict(sorted(finalDict.items(), key=itemgetter(1),reverse=True))# add
            #now sort the secondary location list
            secondary_loc_dict = OrderedDict()
            static_loc_dict = OrderedDict()
            """ Create two dictionaries for the location lists"""



            for i in lastdict:
                if i in concordances[1]:

                    secondary_loc_dict[i]=(concordances[1][i])# append the list#

                if i in concordances[2]:

                    static_loc_dict[i]= (concordances[2])[i]#write the column locations#

                pass
        except Exception as e:
            self.out3.set("Error building concordances")
            self.errorRespond(e)

        return (lastdict,final_locDict, secondary_loc_dict,static_loc_dict)# return the tuple. first element is the sorted Dict, second is the location list, third is sorted loc list,4th is hard locations
        #0---------------------------end BUILDCONCORDANCE-------------------------#

    def writeMatrix(self,matrix_dict,beat,track,file_out="matrix_out.csv"):
        """@params list. Writes a matrix to a csv file, returns dict with dicts of locations"""
        try:
            self.out2.set("Writing to out files")
            file_out = file_out.split(".")[0] + "b" + str(beat) + "t" + str(track) + ".csv"

            with open(file_out,'w+',newline='') as csvfile: #open the csv file
                spamwriter = csv.writer(csvfile)
                for key in matrix_dict[0]: # loop through the keys in the dictionary
                    new_list =  [matrix_dict[0][key]] + key.split(",")#split them by , matrix_dict[0][key] +
                    """EDIT THIS.MAKE IT right this disregarding line length"""# ALREADY EDITED

                    spamwriter.writerow(new_list)
            # Now write the location list to a file
            loc_file_out=file_out.split(".")[0] + "_locationlist.csv"#get the name of the output file and update the name with location

            with open(loc_file_out,'w+',newline='') as csvfile:
                spamwriter = csv.writer(csvfile)
                for line in matrix_dict[1]:#access the list of strings

                    next_row = line.split(",")

                    spamwriter.writerow(next_row)# write the rows


            loc_file_sorted = file_out.split(".")[0] + "_locationlistsorted.csv"

            loc_dict = OrderedDict()
            with open(loc_file_sorted,'w+',newline='') as csvfile:
                spamwriter = csv.writer(csvfile)
                for key in matrix_dict[2]:
                    new_list = key.replace(","," ")
                    loc_list = []
                    loc_list.append(new_list)
                    for item in matrix_dict[2][key].split(","):
                        loc_list.append(item)

                    loc_dict[key] = loc_list[1:]
                    spamwriter.writerow(loc_list)
            loc_hard_file = file_out.split(".")[0] + "_referenceList.csv"

            with open(loc_hard_file,'w+',newline='') as csvfile:
                spamwriter = csv.writer(csvfile)
                for key in matrix_dict[3]:
                    new_list = key.replace(","," ")
                    loc_list = []
                    loc_list.append(new_list)
                    for item in matrix_dict[3][key].split(","):
                        loc_list.append(item)

                    spamwriter.writerow(loc_list)

            self.out2.set("Phase 1 finished")
        except Exception as e:
            self.out2.set("Error occured while writing to disk")
            self.errorRespond(e)
        return loc_dict
        #0---------------------------end WRITEMATRIX-------------------------#

    def processTrack(self,beat,track,interval):
        """Process the tracks with a beat level"""
        print(self.saveLoc[0])
        self.out2.set("Processing Track")
        print("processing track")
        try:

            #call loadData to load the matrix in memory
            print(self.openLoc[0])
            cols = self.loadData(self.openLoc[0])# load the file
            #process the matrix
            concordance = self.processMatrix(cols,beat, track,interval)
            #build a sorted dictionary and corresponding location lists
            finallist=self.buildConcordance(concordance)
            # write both to separate files
            loc_data =self.writeMatrix(finallist,beat,track,self.saveLoc[0])
            return (finallist,loc_data)
        except Exception as e:
            print(e)
            self.errorRespond(e)
            tb = traceback.format_exc()
            print(tb)
            self.errorRespond(tb)
            sys.exit(0)


    def processOverlap(self,bass_track,melody_track,beat_level):
        """ @args  dictionary bass, dictionary melody, int beat_level. returns a list of lists(matrix)"""

        matrix = []#our list of lists


        loop_counter=1

        limit_counter =0
        bass_limit_counter =0
        print(len(bass_track))
        print(len(melody_track))


        # to do: make temporary local variables for the globals and assign at the end
        """bass tracks and melody tracks are dictionaries with a list of locations as values"""
        max_counter = len(bass_track)
        for bass_pattern in bass_track: #loop through the keys
            #future optimizatons. partition bass_track into x slices where x = #cpu cores. use multiprocessing and run in parallel. then join all x jobs
            #if loop_counter>100: #break the loop if its over 100
             #   break
            self.out2.set("Analyzing..." + str(loop_counter) + " of " + str(max_counter))
            bass_counter=0 # total count of this patterns overlaps
            next_row=[]
            next_row.append(bass_pattern)
            bass_list = bass_track[bass_pattern]# get the bass location list
            for melody_pattern in melody_track: # loop through these keys also
                counter =0

                melody_list=melody_track[melody_pattern]#get the melody location list
                """Now loop through both lists and get a count of the number of locations within beat_level steps"""
                for b_item in bass_list:
                    for m_item in melody_list:
                        if abs(float(b_item)-float(m_item)) < beat_level or compFloat(float(b_item),float(m_item)):
                            counter+=1
                            bass_counter+=1 #increment the bass counter
                next_row.append(counter)#append the counter of this match
                self.local_countvaluetable[(bass_pattern,melody_pattern)] = counter #update the entries in the dictionary

                #add the update right here
                #if localmelody[melody] not in table, assign it
                #else ++ the data
                if melody_pattern in self.local_melodytable:
                    self.local_melodytable[melody_pattern]+= counter
                else:
                    self.local_melodytable[melody_pattern] = counter
                limit_counter+=1

                if limit_counter==partition_counter: # here we clear the table and serialize
                    fh= open(self.base_store_file + str(self.file_counter) + '.p','wb')#file handler
                    p=pickle.Pickler(fh,2)
                    p.dump(self.local_countvaluetable)
                    p.memo.clear()
                    self.local_countvaluetable.clear()
                    #pickle.dump(local_countvaluetable,open(base_store_file + str(file_counter) + '.p','wb'),protocol=2)# store the dict temporarily
                    #local_countvaluetable.clear()#clear the dict
                    fh.close()
                    self.file_counter+=1
                    limit_counter=0

                self.total_counter+=counter#update the total counter

            #write the excess values
            if limit_counter-len(self.local_countvaluetable.keys()) > 0:
                pickle.dump(self.local_countvaluetable,open(base_store_file + str(self.file_counter) + '.p','wb'),protocol=2)# store the dict temporarily
                self.local_countvaluetable.clear()#clear the dict
                self.file_counter+=1


            matrix.append(next_row)# add the entire next row of the matrix


            #here we're doing some 32bit optimization if we used over 200mb of memore for our matrix, write it to file
            if len(matrix) *LIST_SIZE*(len(melody_track) * INT_SIZE) > matrix_partition_counter:
                fh= open(self.base_matrix_file + str(self.matrix_file_counter) + '.p','wb')#file handler
                p=pickle.Pickler(fh,2)
                p.dump(matrix)
                p.memo.clear()
                matrix.clear()
                    #pickle.dump(local_countvaluetable,open(base_store_file + str(file_counter) + '.p','wb'),protocol=2)# store the dict temporarily
                    #local_countvaluetable.clear()#clear the dict
                fh.close()
                self.matrix_file_counter+=1



            self.local_basstable[bass_pattern] = bass_counter# add this pattern with its total counter to the dict
            loop_counter+=1

        """ Now we need to get the melody counts. Since the melody table was in the innerloop we couldnt calculate it without adding an inner for loop which would have resulted in n^3 """
        """ loop through the bass paterns using melody patterns as the outerloop. Access the countvaluetable"""
        # We also need to reload the local_countvalue table


        print("Done with initial phase of process overlap")

        if len(matrix)  >0:
            fh= open(self.base_matrix_file + str(self.matrix_file_counter) + '.p','wb')#file handler
            p=pickle.Pickler(fh,2)
            p.dump(matrix)
            p.memo.clear()
            matrix.clear()
            fh.close()
            self.matrix_file_counter+=1
        print("Done with 2nd phase of process overlap")


    # Now assign to the global variables
       # global countvaluetable# set the dictionary for writing
        print("done processing overlap")
        self.out2.set("Done analyzing")
        #return matrix
#------------------------------------------end processoverlap-------------------------------------------------------------------

    def outputOverlap(self,row_headers,column_headers):
        """@args dictionary, header list, column list. Outputs csv"""

        # first output the first 100
        file_out= self.saveLoc[0]
        file_out=file_out.split(".")[0] + "Overlap100" + ".csv"
        counter = 0
        """Store the output files"""
        self.out2.set("Writing top 100 to " + file_out)
        with open(file_out,'w+',newline='') as csvfile: #open the csv file
            spamwriter = csv.writer(csvfile)
            row_headers.insert(0,"")
            spamwriter.writerow(row_headers[:99])
            fh= open(self.base_matrix_file + str(0) + '.p','rb')#file handler
            p=pickle.Unpickler(fh)
            matrix = p.load()
            for row in matrix: # loop through the lists inside the matrix
                try:
                    spamwriter.writerow(row[:99] ) # write the list
                    counter+=1
                    if counter > 99:
                        break
                except Exception as e:
                    self.logger.error(e)
                    tb = traceback.format_exc()
                    self.logger.error(tb)
                    pass

            p.memo.clear()#clear all references
            matrix.clear()#clear the list. Remember we're limited to 200MB
            fh.close()#close the fileoutput



        file_out= self.saveLoc[0]
        file_out=file_out.split(".")[0] + "Overlap" + ".csv"
        #header = row_headers
        """Store the output files"""
        self.out2.set("Writing all values to file " + file_out)
        with open(file_out,'w+',newline='') as csvfile: #open the csv file
            spamwriter = csv.writer(csvfile)
            row_headers.insert(0,"")
            spamwriter.writerow(row_headers)
            for x in range(0,self.matrix_file_counter):
                fh= open(self.base_matrix_file + str(x) + '.p','rb')#file handler
                p=pickle.Unpickler(fh)
                matrix = p.load()
                for row in matrix: # loop through the lists inside the matrix
                    spamwriter.writerow(row ) # write the list
                p.memo.clear()#clear all references
                matrix.clear()#clear the list. Remember we're limited to 200MB
                fh.close()#close the fileoutput
        print("done writing overlaps")
#--------------------------end output Overlap-------------------------------#

    def getPTable(self,bass_track,melody_track):
        """returns a dictionary of ptables from a matrix"""
        print("Getting ptable")

        pMatrix = []
        #pTable = dict()

        loopcounter=1
        """first fisher test matrix paramaters"""
        b_m_intersec = 0#the first entry of the first matrix for the fisher test. intersection count of b_m
        m_total =0#the second entry of the first matrix for the fisher test
        """ second matrix fisher test paramaters"""
        total_b_m_intersec=0#the first entry for the second matrix for the fisher test. count of all intersections in bass pattern in b_m intersec
        m_count_diff=0#4th paramater. count of entire matrix- intersection counter
        max_counter = len(bass_track)

        for bass_pattern in bass_track: #loop through the keys
            self.out2.set("Analyzing pValues... " + str(loopcounter) + "of" + str(max_counter) )
            bass_column_count = self.local_basstable[bass_pattern]
            #if loop_counter>100: #break the loop if its over 100
                #break
            next_row=[]
            next_row.append(bass_pattern)#Can optimize this by storing a reference to the function here
            for melody_pattern in melody_track: # loop through these keys also
                melody_row_count = self.local_melodytable[melody_pattern]
                if (bass_pattern,melody_pattern) in self.local_countvaluetable:
                    b_m_intersec = self.local_countvaluetable[(bass_pattern,melody_pattern)]#get the intersection count
                else:
                    for x in range(0,self.file_counter):
                        self.local_countvaluetable.clear()
                        fh= open(self.base_store_file + str(x) + '.p','rb')#file handler
                        p=pickle.Unpickler(fh)#load the file
                        self.local_countvaluetable=p.load()
                        p.memo.clear()#clear memory

                        fh.close() #unload
                        #local_countvaluetable = pickle.load(open(base_store_file + str(x)+ ".p", 'rb'))
                        if (bass_pattern,melody_pattern) in self.local_countvaluetable: # assume that the value exists in one of these
                            b_m_intersec = self.local_countvaluetable[(bass_pattern,melody_pattern)]#get the intersection count
                            break
                total_b_m_intersec = bass_column_count - b_m_intersec #get the bass column total - intersection count
                m_total = self.local_melodytable[melody_pattern] - b_m_intersec#row total count - intersection count
                m_count_diff = self.total_counter - bass_column_count - melody_row_count+ b_m_intersec#total intersection count-counts of bass, rows
                try:
                    pvalue = (stats.fisher_exact([[b_m_intersec,m_total],[total_b_m_intersec,m_count_diff]]))[1]
                except  Exception as ex:
                    pvalue=1
                    print("Error calculating certain pvalues" )
                    print(ex)
                    self.errorRespond(ex)
                #pTable[(bass_pattern,melody_pattern)]= pvalue
                next_row.append(pvalue)
            #here calculate the pvalue and store as a tuple entry in pMatrix
            pMatrix.append(next_row)# add the entire next row of the matrix
            loopcounter+=1
            #store our temp results to the disk
            if len(pMatrix) *LIST_SIZE*(len(melody_track) * FLOAT_SIZE) > matrix_partition_counter:
                fh= open(self.p_matrix_file + str(self.pmatrix_file_counter) + '.p','wb')#file handler
                p=pickle.Pickler(fh,2)
                p.dump(pMatrix)
                p.memo.clear()
                pMatrix.clear()

                fh.close()
                self.pmatrix_file_counter+=1

        if len(pMatrix)  >0:
            fh= open(self.p_matrix_file + str(self.pmatrix_file_counter) + '.p','wb')#file handler
            p=pickle.Pickler(fh,2)
            p.dump(pMatrix)
            p.memo.clear()
            pMatrix.clear()
            fh.close()
            self.pmatrix_file_counter+=1
        self.out2.set("Done analyzing PValues")
        print("Done analyzing pvalues")

    def outputPTable(self,row_headers,column_headers):
        """Takes a dictionary, and 2 lists containing row and column headers. Outputs csv"""

        #first output the first 100
        matrix=list()
        file_out= saveLoc[0]
        file_out=file_out.split(".")[0] + "PTable100" + ".csv"
        #header = row_headers
        self.out2.set("Writing top 100 pvalues to " + file_out)
        """Store the output files"""
        with open(file_out,'w+',newline='') as csvfile: #open the csv file
            spamwriter = csv.writer(csvfile)
            row_headers.insert(0,"")
            spamwriter.writerow(row_headers[:99])
            for x in range(0,self.pmatrix_file_counter):
                fh= open(self.p_matrix_file+ str(x) + '.p','rb')#file handler
                p=pickle.Unpickler(fh)
                matrix = p.load()
                for row in matrix: # loop through the lists inside the matrix
                    spamwriter.writerow(row ) # write the list
                p.memo.clear()#clear all references
                matrix.clear()#clear the list. Remember we're limited to 200MB
                fh.close()#close the fileoutput

        file_out= saveLoc[0]
        file_out=file_out.split(".")[0] + "PTable" + ".csv"
        #header = row_headers
        self.out2.set("Writing all pValues to " + file_out)
        """Store the output files"""
        with open(file_out,'w+',newline='') as csvfile: #open the csv file
            spamwriter = csv.writer(csvfile)
            row_headers.insert(0,"")
            spamwriter.writerow(row_headers)
            for x in range(0,self.pmatrix_file_counter):
                fh= open(p_matrix_file+ str(x) + '.p','rb')#file handler
                p=pickle.Unpickler(fh)
                matrix = p.load()
                for row in matrix: # loop through the lists inside the matrix
                    spamwriter.writerow(row ) # write the list
                p.memo.clear()#clear all references
                matrix.clear()#clear the list. Remember we're limited to 200MB
                fh.close()#close the fileoutput



    #---------------------------end outputPTable---------------------------------#

    def cleanUp(self):
        """Here we clear out the temporary files"""

        self.out1.set("Cleaning temp files(pass 1) ")
        print("File counter: " + str(self.file_counter))

        for x in range(0,self.file_counter):
            try:
                #print("Clean file" + str(file_counter))

                os.remove(self.base_store_file + str(x)+ ".p")
                self.out2.set("Removed file" + str(x+1) +  "out of " + str(file_counter))
            except  Exception as e:
                print(e)
                self.errorRespond(e)
        self.out1.set("Cleaning temp files(pass 2) ")
        for x in range(0,self.matrix_file_counter):
            try:
                #print("Clean file" + str(matrix_file_counter))
                os.remove(self.base_matrix_file + str(x)+ ".p")
                self.out2.set("Removed file" + str(x+1) +  "out of " + str(self.matrix_file_counter))
            except Exception as e:
                print(e)
                self.errorRespond(e)

        self.out1.set("Cleaning temp files(pass 3) ")
        for x in range(0,self.pmatrix_file_counter):
            try:
                #print("Clean file" + str(matrix_file_counter))
                os.remove(self.p_matrix_file + str(x)+ ".p")
                self.out2.set("Removed file" + str(x+1) +  "out of " + str(self.pmatrix_file_counter))
            except Exception as e:
                print(e)
                self.errorRespond(e)
        self.out1.set("Cleanup finished")


    def startProgram(self,root,args):
        """This function starts the program and returns a tuple of concordances,locationList"""
        self.thread_tk=Thread(target=self.start,args=(self.root,))
        self.thread_tk.start()


    def start(self,root):

        starttime = time.clock()#start the clock
        try:
            if self.chkp1.get()==1:

                print("STarting phase 1")
                self.out1.set("Working: Phase 1 ")
                beat = int(self.beats.get())
                interval = int(self.conc_length.get())
                self.root.withdraw()
                self.winref.deiconify()
                pool = ThreadPool()#processes=number of cores on cpu
                """ Run two separate threads. Analyze the bass and melody tracks concurrently using a threadpool"""
                self.base_matrix_file = self.saveLoc[0].split(".")[0] + self.base_matrix_file
                self.base_store_file = self.saveLoc[0].split(".")[0] + self.base_store_file
                self.p_matrix_file = self.saveLoc[0].split(".")[0] + self.p_matrix_file
                bassStructure = pool.apply_async(self.processTrack,(beat, 0,interval)) # tuple of args.return out tuple of matrices
                melodyStructure = pool.apply_async(self.processTrack,(beat,1,interval))
                pool.close()#no more processes being accepted
                pool.join()#wait for the threads to join. blocks all input from this thread
                if self.chkp2.get() ==1:

                    print("STarting phase 2")
                    self.out1.set("Working: Phase 2 ")
                    self.processOverlap(melodyStructure.get()[1],bassStructure.get()[1],beat)
                    print("Done processing overlap. ")
                    print("Calling outputOverlap")
                    self.outputOverlap(list(bassStructure.get()[1].keys()),None)
                    print("Finished outputOverlap")
                    if self.chkp3.get()==1:
                        print("STarting phase 3")
                        self.out1.set("Working: Phase 3 ")
                        self.getPTable(melodyStructure.get()[1],bassStructure.get()[1])
                        self.outputPTable(list(bassStructure.get()[1].keys()),None)
                        """output Overlap updates our global table data"""


                self.cleanUp()#cleanup the temporary files
            else:
                print("Processing Track")
                tracknum = int(self.track[0].get())
                beat = int(self.beats[0].get())
                interval = int(self.conc_length[0].get())
                self.root.destroy()
                self.base_matrix_file = self.saveLoc[0].split(".")[0] + self.base_matrix_file
                self.base_store_file = self.saveLoc[0].split(".")[0] + self.base_matrix_file
                self.p_matrix_file = self.saveLoc[0].split(".")[0] + self.p_matrix_file
                self.processTrack(beat,tracknum,interval)

            endtime=time.clock()

            print("elapsed:time")
            print(endtime)
            self.out1.set("Finished. Closing in 5.")
            time.sleep(5)
            self.root.destroy()
            os._exit(0)
        except Exception as e:
            print(e)
            tb = traceback.format_exc()
            print(tb)
            self.out3.set("Error in phase 2/3.")
            self.logger.error(e)
            self.logger.error(tb)
            self.cleanUp()
            #errorRespond(e)
            #os._exit(0)
            sys.exit()


    def onExit(self):
        if messagebox.askokcancel("Quit", "Are you sure you want to quit?"):
            self.winref.master.destroy()
            #clean up the thread here
            self.thread_tk.exit()
            #os._exit(0)#quit()
            sys.exit()

    def parse(self):
    #parser test
        queryarguments = list()
        #entry1 = "0,-1,-1,-1;0,1,2,3"
        #entry2 = "0,-1,-1,1; 0,1,2,3"
        #entries = list()
        #entries.append(entry1)
        #entries.append(entry2)
        """ loop through the list box and collect the query results individually"""
        entries = list(self.querylist.get(0, END))
        for item in entries:
            pitchpatterns = item.split(r";")[0].split(r",")#split pattern and rise/fall. Then subsplit into individual items
            n_gramlength = len(pitchpatterns)
            risefall = item.split(r";")[1].split(r",")# array of intervals
            #print(risefall)
            queryarguments.append((pitchpatterns,risefall,n_gramlength))
        return queryarguments

    def query(self,queryarguments):
        """takes: list of tuples of pattern, intervals, and len. Returns locations where query results occurs
            Goal: get a corpus(matrix) and a list of concordances to query.
            Steps: First query for the first concordance. Get the locations from this result and then call process row with the positional argument changed.
            Repeat this for each subset"""
        queryrange = float(self.query_range.get())
        pitchrange = int(self.pitch_range.get())
        qur = iter(queryarguments) #iterator to our query list
        next_suite = next(qur) # next tuple to process. includes pitch patttern, beat pattern
        next_query = next_suite[0]
        relative_start_search_position = 0
        #rise_fall = iter(queryarguments[0][1])

        next_risefall = next_suite[1] #next pitch pattern

        resultlist=list()
        combolist = list()
        templist = list()
        initialresult = None
        length = len(self.nmat)
        #print(queryarguments[0][0])
        for x in range(0,length): # loop through our matrix and find locations of the first query. Store locations in resultlist
            #print("Working row " + str(x) + " out of " + str(length))
            initialresult =self.processQueryRow(next_query,next_risefall,x) # check
            if initialresult is not None:
                #print("valid")
                resultlist.append(initialresult) #

            #gc.collect()
        if len(queryarguments) <2: # if we only had one queryargument, end the search
            #print("One query inserted")
            return resultlist

        next_suite = next(qur) # set iterator to next tuple of data
        next_query = next_suite[0] # get the next query
        next_risefall = next_suite[1] # get the next interval pattern

        #print("Result for query one")
        #print(resultlist)
        while 1: #loop until our list is empty
            try:
                relative_start_search_position = self.getAbsolutePosition(queryrange,resultlist[0][0])#get the absolute position from the first pattern.added
                for x in resultlist: # for all locations found so far, look for successive query patterns starting from them
                    for y in range(relative_start_search_position,length): #for y in range(x[0],length):
                        #relative_start_search_position= self.getAbsolutePosition(queryrange,y)
                        #initialresult =self.processQueryRow(next_query,next_risefall,relative_start_search_position) # check
                        initialresult =self.processQueryRow(next_query,next_risefall,y) # check
                        if initialresult is not None:
                        #print("valid")
                            combolist.append(initialresult) #

                #print("Result for combolist")
                #print(combolist)
                for item in resultlist: # check to see if the results from combolist are within range with the results from result list
                    for item2 in combolist:
                        #print('comparing ' + str(item[2]) + ' to ' + str(item2[2]) + ' = ' +  str(abs(item[2]) - item2[2] ))
                        if  abs(item[2] - item2[2])<= queryrange and abs(item[1] - item2[1])== pitchrange: #pitchrange is vertical displacement
                            templist.append(item)
                            break
                resultlist.clear()
                resultlist = templist.copy()
                templist.clear()
                combolist.clear()
                next_suite = next(qur)
                next_query = next_suite[0]
                next_risefall = next_suite[1]
            except StopIteration:
                #print("finished")
                return resultlist

        return resultlist

    def processQueryRow(self,concordance,interval_pattern, position):
        """concordance is a list describing the pattern to match. interval pattern is the corresponding interval list. table_data is the matrix,position is the slot in the matrix we are looking for"""

        """     Goal: Analyze a row in the matrix and determine if it is the start of a query result.
                Steps: Get the next pattern to match(1 enntryfromm both concorance and interval pattenr) and inspect the next row seeing if the change in pitch/interval matches the next pattern. If so set a flag , save location, and repeat until
                        next returns bad/null or we go past the max distance allowed. Return the position, and location info
        """
        #import pdb; pdb.set_trace()

        #objgraph.show_growth(limit=10)
        working_row= self.nmat[position] # the row in the table we are analyzing
        current_track = working_row.channel # the track number we will be looking at when analyzing this row
        interval_pattern_ints = [float(nums) for nums in interval_pattern] # convert to numberic format
        #max_distance =  sum(interval_pattern_ints)+ working_row.onset_beats# the maximum distance allowed to find a match
        max_distance = max(interval_pattern_ints) + working_row.onset_beats
        #print(str(max(interval_pattern_ints)) + " : max for this row starting at position " + str(position+1))
        #print (max_distance)
        current_pitch = working_row.pitch# the initial pitch we're starting at
        initial_pitch = float(working_row.pitch)
        initial_piece = int(working_row.piece)
        current_beat=float(working_row.onset_beats)# the starting beat
        beat_iterator = iter(interval_pattern_ints[1:]) # get an iterator to the pitch list
        pitch_iterator = iter(concordance[1:])# get an iterator to the concordance list
        counter = 1

        next_pitch = float(next(pitch_iterator))
        next_beat = float(next(beat_iterator))

        #print("initial pitcj = " + str(current_pitch) + " initial beat = " + str(current_beat))
        for x in range(position+1, len(self.nmat)):
            try:
                current_row = self.nmat[x] # look at the next row in the table to compare to the current row
                current_pitch = current_row.pitch
                #print("Row" + str(position+1))
                #print( "current putch: " + str(current_row.pitch) + "next pitch " + str(next_pitch) + "comparison pitch" + str(current_pitch) +  "current beat: " + str(current_row.onset_beats) + "next beat " + str(next_beat) )
               ## if current_track!=current_row.channel: # skip this row
                 #   print("unveven channel")
                    #continue





                if current_row.piece != initial_piece or current_row.onset_beats> max_distance  :
                    del working_row
                    del current_track
                    interval_pattern_ints.clear()
                    del interval_pattern_ints
                    del current_pitch

                    del pitch_iterator
                    del beat_iterator

                    del next_beat
                    del next_pitch

                    del current_beat
                    del max_distance
                    del current_row
                    return None# end the search query



                if compFloat(current_row.pitch,next_pitch + initial_pitch)  and compFloat(current_row.onset_beats ,next_beat + current_beat) :# check to see if the pitches match.

                    counter+=1
                    if counter==len(concordance):

                        return (position+1,initial_pitch,current_beat)
                    next_pitch = float(next(pitch_iterator))
                    next_beat = float(next(beat_iterator))



            except StopIteration:

                if counter == len(concordance):
                    return x
                return None

            except Exception as e:
                self.errorRespond(e)
                tb = traceback.format_exc()
                #print(tb)
                self.errorRespond(tb)


                return None


        return None

    def phaseIV(self):



       args = self.parse()

       self.loadData(self.openLoc[0])
       print(self.openLoc[0])
       outtext= self.query(args)
       print(outtext)
       fname = 'QueryOut.txt'
       with open(fname,'a+') as f:
           for item in outtext:
               f.write(str(item[0]) + ':' + str(item[1]) )

    def getAbsolutePosition(self,displacement_max,startposition,):
        """ Searches for a position in the matrix to search relative to a starting point.
            arg1: beat displacement max, arg2: starting position to begin search at
        """
        lastposition = startposition
        max_val_to_find = self.nmat[startposition].onset_beats - displacement_max
        for x in range(startposition,0,-1):
            if self.nmat[lastposition].onset_beats >= max_val_to_find :
                lastposition = x
            else:
                break

        return lastposition

        pass



def main():
    x=ConcordanceApp()
    try:


        x.initialize()
        x.root.mainloop()

    except Exception as e:
        tb = traceback.format_exc()
        print(e)
        print(tb)
        #x.cleanUp()
        print("successfully cleaned resources")
        #os._exit(0)

    sys.exit()






if __name__ == '__main__':
    main()



