#!/usr/bin/env python2

'''

This script analyzes data acquired using movingBar_tmp.py.

It is the longer way of doing FFT (akin to fiedmap_demodulate_orig.py)

It creates maps based on reversal directions of vertical and horizontal bars.

Run:  python make+maps.py /path/to/imaging/directory

It will output change in response to...

'''

import numpy as np
import os
from skimage.measure import block_reduce
from scipy.misc import imread
import cPickle as pkl
import scipy.signal
import numpy.fft as fft
import sys
import optparse
from libtiff import TIFF
from PIL import Image
import re
import itertools
from scipy import ndimage

import math
import matplotlib as mpl
import matplotlib.pylab as plt
import matplotlib.cm as cm
import pandas as pd

def movingaverage(interval, window_size):
    window = np.ones(int(window_size))/float(window_size)
    return np.convolve(interval, window, 'valid')


parser = optparse.OptionParser()
parser.add_option('--headless', action="store_true", dest="headless", default=False, help="run in headless mode, no figs")
parser.add_option('--reduce', action="store", dest="reduce_val", default="2", help="block_reduce value")
parser.add_option('--sigma', action="store", dest="gauss_kernel", default="0", help="size of Gaussian kernel for smoothing")
parser.add_option('--format', action="store", dest="im_format", default="tif", help="saved image format")
parser.add_option('--bar', action="store_true", dest="bar", default=False, help="moving bar stimulus or not")
parser.add_option('--custom', action="store_true", dest="custom_keys", default=False, help="custom keys for condition runs or not")
parser.add_option('--run', action="store", dest="run_num", default=1, help="run number for current condition set")

parser.add_option('--up', action="store", dest="up_key", default=1, help="if more than one run, run number")
parser.add_option('--down', action="store", dest="down_key", default=1, help="if more than one run, run number")
parser.add_option('--left', action="store", dest="left_key", default=1, help="if more than one run, run number")
parser.add_option('--right', action="store", dest="right_key", default=1, help="if more than one run, run number")

(options, args) = parser.parse_args()

bar = options.bar
im_format = '.'+options.im_format
headless = options.headless
reduce_factor = (int(options.reduce_val), int(options.reduce_val))
if reduce_factor[0] > 0:
	reduceit=1
else:
	reduceit=0
gsigma = int(options.gauss_kernel)
if headless:
	mpl.use('Agg')

custom_keys = options.custom_keys
if custom_keys:
	up_key = str(options.up_key)
	down_key = str(options.down_key)
	left_key = str(options.left_key)
	right_key = str(options.right_key)
run_num = str(options.run_num)


#################################################################################
# GET PATH INFO:
#################################################################################
outdir = sys.argv[1]
files = os.listdir(outdir)
files = [f for f in files if os.path.splitext(f)[1] == '.pkl']

rundir = os.path.split(outdir)[0]
sessiondir = os.path.split(rundir)[0]


#################################################################################
# GET BLOOD VESSEL IMAGE:
#################################################################################

folders = os.listdir(sessiondir)
figdir = [f for f in folders if f == 'figures'][0]
ims = os.listdir(os.path.join(sessiondir, figdir))
print ims
impath = os.path.join(sessiondir, figdir, ims[0])
# image = Image.open(impath) #.convert('L')
# imarray = np.asarray(image)
if os.path.splitext(impath)[1] == '.tif':
	tiff = TIFF.open(impath, mode='r')
	imarray = tiff.read_image().astype('float')
	tiff.close()
	plt.imshow(imarray)
else:
	image = Image.open(impath) #.convert('L')
	imarray = np.asarray(image)

# files = os.listdir(outdir)

# # GET BLOOD VESSEL IMAGE:
# ims = [f for f in files if os.path.splitext(f)[1] == str(im_format)]
# print ims
# impath = os.path.join(outdir, ims[0])
# image = Image.open(impath).convert('L')
# imarray = np.asarray(image)

# GET DATA STRUCT FILES:
# sessions = [f for f in flist if os.path.splitext(f)[1] != '.png']
# session_path = os.path.join(outdir, sessions[int(0)]) ## LOOP THIS


#################################################################################
# GET DATA STRUCT FILES:
#################################################################################

#files = os.listdir(outdir)
files = [f for f in files if os.path.splitext(f)[1] == '.pkl']
dstructs = [f for f in files if 'D_target' in f and str(reduce_factor) in f]
if not dstructs:
	dstructs = [f for f in files if 'D_' in f and str(reduce_factor) in f] # address older analysis formats

print dstructs

D = dict()
for f in dstructs:
	outfile = os.path.join(outdir, f)
	with open(outfile,'rb') as fp:
		D[f] = pkl.load(fp)
# close

# MATCH ELEV vs. AZIM conditions:
ftmap = dict()
outshape = D[D.keys()[0]]['ft_real'].shape
for curr_key in D.keys():
	reals = D[curr_key]['ft_real'].ravel()
	imags = D[curr_key]['ft_imag'].ravel()
	ftmap[curr_key] = [complex(x[0], x[1]) for x in zip(reals, imags)]
	ftmap[curr_key] = np.reshape(np.array(ftmap[curr_key]), outshape)

if bar:

	if custom_keys:
		V_keys = [up_key, down_key]
		H_keys = [left_key, right_key]
	else:
		V_keys = [k for k in ftmap.keys() if 'V' in k and '_'+run_num in k]
		H_keys = [k for k in ftmap.keys() if 'H' in k and '_'+run_num in k]

	azimuth_phase = np.angle(ftmap[V_keys[0]] / ftmap[V_keys[1]])
	elevation_phase = np.angle(ftmap[H_keys[0]] / ftmap[H_keys[1]])

	aztitle = 'azimuth'
	eltitle = 'elevation'

else:

	blank_key = [k for k in ftmap.keys() if 'blank' in k]
	stim_key = [k for k in ftmap.keys() if 'stimulus' in k]
	
	azimuth_phase = np.angle(ftmap[stim_key[0]])
	elevation_phase = np.angle(ftmap[blank_key[0]])

	aztitle = 'stimulus'
	eltitle = 'blank'




# freqs = D[V_keys[0]]['freqs']
# target_freq = D[V_keys[0]]['target_freq']
# target_bin = D[V_keys[0]]['target_bin']


#################################################################################
# PLOT IT:
#################################################################################
# plt.figure()

# plt.subplot(1,3,1) # GREEN LED image
# plt.imshow(imarray,cmap=cm.Greys_r)

# plt.subplot(1,3,2) # ABS PHASE -- elevation
# fig = plt.imshow(elevation_phase, cmap="spectral")
# plt.colorbar()
# plt.title(eltitle)

# plt.subplot(1,3,3) # ABS PHASE -- azimuth
# fig = plt.imshow(azimuth_phase, cmap="spectral")
# plt.colorbar()
# plt.title(aztitle)

# # SAVE FIG 1
# sessionpath = os.path.split(outdir)[0]
# plt.suptitle(sessionpath)

# outdirs = os.path.join(sessionpath, 'figures')
# which_sesh = os.path.split(sessionpath)[1]
# print outdirs
# if not os.path.exists(outdirs):
# 	os.makedirs(outdirs)
# # imname = which_sesh  + '_mainmaps_' + str(reduce_factor) + '.svg'
# # plt.savefig(outdirs + '/' + imname, format='svg', dpi=1200)
# imname = which_sesh  + '_mainmaps_' + str(reduce_factor) + '.png'
# plt.savefig(outdirs + '/' + imname, format='png')
# print outdirs + '/' + imname

# plt.show()


# GET ALL RELATIVE CONDITIONS:
plt.figure()

# if bar: 

# 	plt.subplot(3,4,1) # GREEN LED image
# 	plt.imshow(imarray,cmap=cm.Greys_r)

# 	plt.subplot(3,4,2) # ABS PHASE -- elevation
# 	fig = plt.imshow(elevation_phase, cmap="spectral")
# 	plt.colorbar()
# 	plt.title(eltitle)

# 	plt.subplot(3, 4, 3) # ABS PHASE -- azimuth
# 	fig = plt.imshow(azimuth_phase, cmap="spectral")
# 	plt.colorbar()
# 	plt.title(aztitle)

	# plt.show()

if bar:

	# PHASE:
	for i,k in enumerate(H_keys): #enumerate(ftmap.keys()):
		plt.subplot(2,2,i)
		phase_map = np.angle(ftmap[k]) #np.angle(complex(D[k]['ft_real'], D[k]['ft_imag']))
		mag_map = D[k]['mag_map']

		hue = (phase_map - phase_map.min()) / (phase_map.max() - phase_map.min())
		sat = np.ones(hue.shape) #*0.5
		val = (mag_map - mag_map.min()) / (mag_map.max() - mag_map.min())

		HSV = np.ones(val.shape + (3,))
		HSV[...,0] = hue
		HSV[...,2] = sat
		HSV[...,1] = val

		#plt.figure()
		fig = plt.imshow(HSV)
		plt.title('combined_'+k)
		plt.colorbar()


	for i,k in enumerate(V_keys): #enumerate(ftmap.keys()):
		plt.subplot(2,2,i+2)
		mag_map = D[k]['mag_map']

		hue = (phase_map - phase_map.min()) / (phase_map.max() - phase_map.min())
		sat = np.ones(hue.shape) #*0.5
		val = (mag_map - mag_map.min()) / (mag_map.max() - mag_map.min())

		HSV = np.ones(val.shape + (3,))
		HSV[...,0] = hue
		HSV[...,2] = sat
		HSV[...,1] = val


		#plt.figure()
		fig = plt.imshow(HSV)
		plt.title('combined_'+k)
		plt.colorbar()

	plt.show()

	# # MAG:
	# for i,k in enumerate(H_keys): #enumerate(D.keys()):
	# 	plt.subplot(3,4,i+9)
	# 	mag_map = D[k]['mag_map']
	# 	fig = plt.imshow(mag_map, cmap=cm.Greys_r)
	# 	plt.title(k)
	# 	plt.colorbar()

	# for i,k in enumerate(V_keys): #enumerate(D.keys()):
	# 	plt.subplot(3,4,i+11)
	# 	mag_map = D[k]['mag_map']
	# 	fig = plt.imshow(mag_map, cmap=cm.Greys_r)
	# 	plt.title(k)
	# 	plt.colorbar()

	#plt.suptitle(session_path)


	# sessionpath = os.path.split(outdir)[0]
	# plt.suptitle(sessionpath)

	# SAVE FIG
	# outdirs = os.path.join(sessionpath, 'figures')
	# which_sesh = os.path.split(sessionpath)[1]
	# print outdirs
	# if not os.path.exists(outdirs):
	# 	os.makedirs(outdirs)

# 	imname = which_sesh  + '_HSV_run' + str(run_num) + '_' + str(reduce_factor) + '.svg'
# 	plt.savefig(outdirs + '/' + imname, format='svg', dpi=1200)
# #	print outdirs + '/' + imname
# #	plt.show()

# 	imname = which_sesh  + '_HSV_run' + str(run_num) + '_' + str(reduce_factor) + '.png'
# 	plt.savefig(outdirs + '/' + imname, format='png')
# 	print outdirs + '/' + imname
# 	plt.show()


