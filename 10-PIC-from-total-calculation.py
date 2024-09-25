# -*- coding: utf-8 -*-
"""
Created on Wed Sep 18 16:01:46 2024
This script should read in a re-formatted csv from an analyses lab (probably UMaine) and spit out sea water corrected PIC in ug/l.

It follows the steps laid out in the calculation excel sheet PIC SeaWater Correction - Balch Lab Template.xlsx

The excel file we get from UMaine is rather poorly formatted, and needs to be copy-pasta'ed into a more readable format. 

How much do we want to do via pop-ups a la the PSICAM Rho calc sheet?

We may need to break up the samples into their own categories such as different cruises (if we send in batches) or types of deployments (surface samples vs. CTDs, etc.)
@author: fmiller
"""

#%% Load Depndancies
import pandas as pd
import numpy as np
import easygui

#%% Load re-formatted csv
#Is there a way to auto load the orginial? Perhaps it's not in a reliable format...
UMO_file = easygui.fileopenbox(title = "PIC file from UMaine", default = "Z:\\projects\\", filetypes = ["*.xlsx"])
data_in = pd.read_excel(UMO_file, usecols = [0,1,2,3,4], skiprows = 5, header = None)
data_in.columns = ["Tube Number", "Ca", "Sr", "Mg", "Na"]

#%% Metadata extraction and tagging of samples
#here we need to be sure all metadata is correctly formatted and alligned with the data. Anything stored in the sample names should be extracted
#also if samples come back without sample names, just tube numbers, can we match it up automatically? Maybe even check for discrepencies?

metadata = pd.read_excel("Z:\\projects\\CHALKY\\data\\PIC\\PIC sample logsheet.xlsx")

data_all = pd.merge(metadata, data_in) #This merge matches on common columns, in this case only "Tube Number". It also removes all the "lab blank" and "QC" rows, which is nice. It will remove anything that does not have a tube number.
#%% Blank identifcation and averaging
#Be careful here because there are numerious "lab blank" and others that are not filter or media blanks...
#Do we make a standard "blank" name that gets identified?
#Need ca_blank, mg_blank, sr_blank, na_blank

blanks = data_all[data_all['Station'].str.contains('blank', case = False)] #Only blanks
ca_blank = blanks['Ca'].mean()
mg_blank = blanks['Mg'].mean()
sr_blank = blanks['Sr'].mean()
na_blank = blanks['Na'].mean()

#Putt data without blanks
data = data_all[~data_all['Station'].str.contains('blank', case = False)] #data without blanks

#%% Pull out vectors
#All raw values of elements
#Gotta NOTinclude the blanks!
ca_raw = data['Ca']
mg_raw = data['Mg']
sr_raw = data['Sr']
na_raw = data['Na']

#Volumes next
vol_filt = data['Filter Volume']
vol_ext = 5 #Do we need this to be variable ever?



#%% Add in standard salt water corrections for calcium, magnesium, and stronium
#First remove blanks, ca mg sr and na
blank_removed = {
    'Ca': ca_raw - ca_blank,
    'Mg': mg_raw - mg_blank,
    'Sr': sr_raw - sr_blank,
    'Na': na_raw - na_blank
}

na_ratio = blank_removed['Na'] / 10784
#Next we get the ratios
element_ratios = {
    'Ca': blank_removed['Ca'] - (na_ratio * 412),
    'Mg': blank_removed['Mg'] - (na_ratio * 1284),
    'Sr': blank_removed['Sr'] - (na_ratio * 7.9)
}
#na_ratio = na_blank_removed / 10784
#Then na_ratio * metal_specific_value:
    #ca value gets * 412
    #mg is * 1284
    #sr * 7.9
    # = something like ca_na_ratio, mg_na_ratio, sr_na_ratio
#Then its ca_blank_removed - ca_na_ratio, etc.

#%% Correct these for volume filtered and extraction volumes
#Where do we get the extraction volume? Is it standard for the analyses? Do we add a column to the csv, or do we program it in?
volume_ratio = vol_ext / vol_filt

#Then ca_corrected * volume_ratio
vol_corrected = {
    'Ca': element_ratios['Ca'] * volume_ratio,
    'Mg': element_ratios['Mg'] * volume_ratio,
    'Sr': element_ratios['Sr'] * volume_ratio
}

#%% Conversion into final desired units
data['PIC (ug/L)'] = vol_corrected['Ca'] * 0.3


#%% Groupby averaging over replicates. Create second dataframe with average and sd.
pic_data = data.drop(['Tube Number', 'replicate'], axis = 1)
pic_mean = pic_data.groupby(['Station', 'Niskin/Subset'], dropna = False).agg(pic_mean = ('PIC (ug/L)', np.mean), pic_sd = ('PIC (ug/L)', np.std)).reset_index()

metadata_trimmed = metadata.drop(['Tube Number', 'replicate', 'notes', 'Filter Volume', 'Unnamed: 7'], axis = 1)

pic_mean_export = pd.merge(pic_mean, metadata_trimmed, on = ['Station', 'Niskin/Subset'], how = "left").drop_duplicates()

#%% Format for file output, including cruise name and cruise directory
#Add back in any metadata that has been lost along the way
pic_mean_export.to_csv("Z:\\projects\\CHALKY\\data\\PIC\\PIC_calculated_mean.csv", index = False)
data.to_csv("Z:\\projects\\CHALKY\\data\\PIC\\PIC_calculated_all.csv", index = False)

#%% File output.
