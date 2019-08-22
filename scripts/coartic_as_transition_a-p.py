#!/usr/bin/env python
# -*- coding: utf-8 -*- #  

'''
# calculate coarticulation as a function of transition time 
# between adjacent phones
# à la Gerosa et al. (2006)
# walk directory of wav files and corresponding textgrids, option to specify single wav file 
# file output = .mean_spectrum.csv
# Authors: Meg Cychosz & Keith Johnson 2019, 
# also includes pieces hobbled together from various scripts 
# of Ronald Sprouse 
# UC Berkeley
'''

import os, sys, fnmatch
import subprocess
import audiolabel
import librosa
import numpy as np
import re
import pandas as pd
from collections import OrderedDict
import matplotlib.pyplot as plt
from sys import argv



# Regex to identify segments
segments = re.compile("a|ch|qh|p|k|t|r|m|w|kh|s",re.IGNORECASE)
words = re.compile("api-pi|chaki-pi|katari-pi|llama-pi|maki-pi|papa-pi|waka-pi|wasi-pi|wawa-pi|imilla-pi|juk'ucha-pi|sunkha-pi|t'ika-pi|uhut'a-pi|wallpa-pi|warmi-pi|wallpa|t'ika|sunkha|wawa|wasi|waka|papa|maki|llama|katari|chaki|api|qhari|qhari-pi|warmi|",re.IGNORECASE)

speakerlist = []
phonelist = []
followinglist = []
prevlist = []
wordlist = []
notelist = []
t1list = []
t2list = []
durlist = []
worddurlist = []
transdur_list = []
morphlist = []




def processwav(wav, tg): # wav = path to the wav file in dir

	f, sr = librosa.load(wav, sr=12000) # load in file and the sampling rate you want
	pm = audiolabel.LabelManager(from_file=os.path.join(dirpath,tg),from_type="praat") # open text grid 

	for word in pm.tier('Word').search(words): 

		t1_idx = np.floor((word.t1)*sr) # Convert time to integer index
		t2_idx = np.floor((word.t2)*sr)
		snippet = f[int(t1_idx):int(t2_idx)]
		snippet_pm = pm.tier('Phone').tslice(word.t1, word.t2, lincl=False, rincl=False)
		
		# get the spectrum
		FFT = librosa.stft(snippet, n_fft=n_fft, hop_length=hop, win_length=window)

		# convolve the filterbank over the spectrum
		S = mel_f.dot(np.abs(FFT))

		# we average over the entire consonant
		def get_spectrum(S,t1,t2,step_size=step_size, plot=False,label='c'):

		    start_frame = np.int(t1/step_size)
		    end_frame = np.int(t2/step_size)

		    mean_mel_spectrum = np.mean(np.log(S[:,start_frame:end_frame]),axis=1)

		    return mean_mel_spectrum

		def get_transition_duration(S,s1,s2,word,step_size,plot=False):

			print(word.text)
			s1start = s1.t1 - word.t1
			s1end = s1.t2 - word.t1
			s1mid = (s1end+s1start)/2
			s2start = s2.t1 - word.t1
			s2end = s2.t2 - word.t1
			s2mid = (s2end+s2start)/2
			
			s1mean = get_spectrum(S,s1start,s1end,step_size=step_size) # xc - get mean c spectrum
			s2mean = get_spectrum(S,s2start,s2end,step_size=step_size) # xv

			start_frame = np.int(s1mid/step_size) 
			end_frame = np.int(s2mid/step_size)

            
            # Gerosa & Narayanan:  fcv(i) = d(xc, xi) − d(xv, xi) where c and v are consonant & vowel and xi is the frame 
			trajectory = []
			for i in np.arange(start_frame,end_frame):
				spec = np.log(S[:,i])  # xi - get that # frame from the spectrum
				d1 = np.linalg.norm(s1mean-spec)  # d(xc,xi) 
				d2 = np.linalg.norm(s2mean-spec)  # d(xv,xi)
				trajectory.append(d1-d2)  # fcv(i)
                
            # may want to plot the trajectory here - sanity check
			#if (plot):   
				#plt.plot(trajectory)
                
			clist = []
			vlist = []
			for num in trajectory:
				if num < 0:
					clist.append(num)
				else:
					vlist.append(num)
			cmean = np.mean(clist)  # mean of fcv in c portion
			vmean = np.mean(vlist) 
			lowbound = cmean*.8 # magic number  - the "fixed threshold"
			highbound = vmean*.8 
            
            # assumption here may be false - all frames under threshold are in the transition
			x = 0
			for num in trajectory:
				if num < highbound and num > lowbound: # only get those values that are within bounds to calculate duration
					x = x + 1

			transition_duration = x*step_size
            
			return transition_duration
            
		#loop through all of the (specified) labels on the "phone" tier of the current word
		for v in snippet_pm: 
			if re.match(segments, v.text) and v.t2 != word.t2: # and if the segment isn't word-final 

				t1=v.t1-word.t1
				t2=v.t2-word.t1

				#spectrum = get_spectrum(S, t1, t2,step_size=step_size)
				trans_dur = get_transition_duration(S, v, pm.tier('Phone').next(v), word, step_size=step_size)
				
				speakerlist.append(wav.split("_", 1)[0]) 
				phonelist.append(pm.tier('Phone').label_at(v.center).text)
				followinglist.append((pm.tier('Phone').next(v)).text)
				prevlist.append((pm.tier('Phone').prev(v)).text)
				wordlist.append(pm.tier('Word').label_at(v.center).text)
				t1list.append(v.t1)
				t2list.append(v.t2)
				notelist.append(pm.tier('Translation').label_at(v.center).text)
				durlist.append(v.t2-v.t1)
				worddurlist.append(word.t2-word.t1)
				transdur_list.append(trans_dur)
				morphlist.append(pm.tier('Morpheme').label_at(v.center).text)




	df = pd.DataFrame( OrderedDict( (('Speaker', pd.Series(speakerlist)),
	('Phone', pd.Series(phonelist)), 
	('Previous',  pd.Series(prevlist)), ('Following',  pd.Series(followinglist)), 
	('Word',  pd.Series(wordlist)), 
	('Translation', pd.Series(notelist)),
	('phone_t1',  pd.Series(t1list)), ('phone_t2',  pd.Series(t2list)), 
	('transition_duration', pd.Series(transdur_list)),
	('Phone_duration',  pd.Series(durlist)), ('Word_duration', pd.Series(worddurlist)),
	('Morph_status', pd.Series(morphlist)))))

	df.to_csv(os.path.splitext(soundfile)[0]+'.trans_dur_sbq.csv', encoding='utf-8') 





# Input wavfile 
filelist = [] # a tuple of wav & tg
if sys.argv[1] == 'walk': # if walk is specified in command line, walk over directory
  for dirpath, dirs, files in os.walk('.'): # walk over current directory
      for soundfile in fnmatch.filter(files, '*.wav'):
          #soundpath = os.path.join(dirpath, soundfile)
          filename = os.path.splitext(soundfile)[0]
          tg = filename+'.TextGrid'  # get the accompanying textgrid
          thing_to_add = (soundfile, tg)
          filelist.append(thing_to_add)
else: # option to run single wav file
  soundfile = sys.argv[1] 
  tg = os.path.splitext(soundfile)[0]+'.TextGrid'  # get the accompanying textgrid
  thing_to_add = (soundfile, tg)
  filelist.append(thing_to_add)
  dirpath = '.'

# define some parameters
sr = 12000 # option to specify desired sampling rate
step_size = 0.003   # 3 ms between spectra
frame_size = 0.0256  # 25.6 ms chunk
hop = np.int(step_size * sr)  
window = np.int(frame_size * sr) 
fmax = np.int(sr/2) # nyquist frequency
fmin = 100
n_fft = 2048 # # of FFT coefficients to compute
n_mels = 29  # # of Mel filter bands

# compute the mel frequency filter bank
mel_f = librosa.filters.mel(sr, n_fft=2048, n_mels=29, fmin=100.0, fmax=6000, htk=True, norm=1)

for wav, tg in filelist: 
      print(wav) # sanity check
      processwav(wav, tg)